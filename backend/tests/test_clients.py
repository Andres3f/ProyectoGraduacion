"""Tests del CRUD de clientes + PostGIS nearby (OPT-8) + geocoding."""

from unittest.mock import patch

from app.services.ors_client import ORSError


def _make_client(client, headers, **overrides):
    payload = {
        "name": f"Cliente {len(overrides)}",
        "address": "Centro, Jalapa",
        "zone": "Centro",
        "latitude": 14.6347,
        "longitude": -89.9889,
    }
    payload.update(overrides)
    return client.post("/api/clients/", json=payload, headers=headers)


def test_create_client(client, admin_headers):
    resp = _make_client(client, admin_headers, name="Cliente Nuevo")
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Cliente Nuevo"
    assert body["latitude"] == 14.6347
    assert body["zone"] == "Centro"


def test_create_client_invalid_coords(client, admin_headers):
    resp = _make_client(client, admin_headers, latitude=95)
    assert resp.status_code == 422
    resp = _make_client(client, admin_headers, longitude=-200)
    assert resp.status_code == 422


def test_create_client_forbidden(client, regular_user_headers):
    resp = _make_client(client, regular_user_headers)
    assert resp.status_code == 403


def test_list_clients_with_filters(client, admin_headers):
    _make_client(client, admin_headers, name="Cliente A", zone="Centro")
    _make_client(client, admin_headers, name="Cliente B", zone="Norte")
    resp = client.get("/api/clients/?zone=Centro", headers=admin_headers)
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == ["Cliente A"]
    resp = client.get("/api/clients/?name=Cliente", headers=admin_headers)
    assert len(resp.json()) == 2


def test_get_client_by_id(client, admin_headers):
    client_id = _make_client(client, admin_headers, name="Detalle").json()["id"]
    resp = client.get(f"/api/clients/{client_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Detalle"


def test_get_client_not_found(client, admin_headers):
    resp = client.get("/api/clients/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_update_client(client, admin_headers):
    client_id = _make_client(client, admin_headers, name="A Editar").json()["id"]
    resp = client.put(
        f"/api/clients/{client_id}",
        json={"name": "Editado", "zone": "Sur"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Editado"
    assert resp.json()["zone"] == "Sur"


def test_delete_client_without_orders(client, admin_headers):
    client_id = _make_client(client, admin_headers, name="A Borrar").json()["id"]
    resp = client.delete(f"/api/clients/{client_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert (
        client.get(f"/api/clients/{client_id}", headers=admin_headers).status_code
        == 404
    )


def test_delete_client_with_orders(client, admin_headers):
    client_id = _make_client(client, admin_headers, name="Con Pedidos").json()["id"]
    resp = client.post(
        "/api/orders/",
        json={
            "client_id": client_id,
            "weight_kg": 100,
            "volume_m3": 2,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    resp = client.delete(f"/api/clients/{client_id}", headers=admin_headers)
    assert resp.status_code == 400


def test_nearby_clients(client, admin_headers):
    _make_client(
        client, admin_headers,
        name="Cerca", latitude=14.6300, longitude=-89.9900, zone="Centro",
    )
    _make_client(
        client, admin_headers,
        name="Lejos", latitude=14.6400, longitude=-89.9900, zone="Norte",
    )
    # Radio de 1 km desde el punto A → solo "Cerca" (~0 m de distancia)
    resp = client.get(
        "/api/clients/nearby?lat=14.6300&lng=-89.9900&radius_km=1",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    names = [c["name"] for c in resp.json()]
    assert names == ["Cerca"]
    # Radio de 5 km → ambos entran
    resp = client.get(
        "/api/clients/nearby?lat=14.6300&lng=-89.9900&radius_km=5",
        headers=admin_headers,
    )
    assert len(resp.json()) == 2


# ── Geocoding (feature/geocoding-clientes) ─────────────────────────────

MOCK_CANDIDATES = [
    {"label": "5ta Calle 2-30, Zona 1, Jalapa, Guatemala", "lat": 14.6350,
     "lng": -89.9880, "confidence": 0.9, "source": "ors"},
    {"label": "5a Avenida 2-30, Jalapa, Guatemala", "lat": 14.6310,
     "lng": -89.9920, "confidence": 0.6, "source": "ors"},
]


def test_geocode_returns_candidates(client, admin_headers):
    # Mockea el proveedor: nunca llamar a ORS/Nominatim real en los tests.
    with patch("app.routers.clients.geocode_address", return_value=MOCK_CANDIDATES):
        resp = client.get(
            "/api/clients/geocode?q=5ta+calle+2-30", headers=admin_headers
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[0]["lat"] == 14.6350
    assert results[0]["source"] == "ors"


def test_geocode_rejects_too_short_query(client, admin_headers):
    resp = client.get("/api/clients/geocode?q=ab", headers=admin_headers)
    assert resp.status_code == 400


def test_geocode_returns_empty_list_when_both_providers_fail(
    client, admin_headers
):
    # ORS y Nominatim caídos → la API responde 200 con [], no un 500.
    with patch(
        "app.routers.clients.geocode_address",
        side_effect=ORSError("ambos proveedores caídos"),
    ):
        resp = client.get(
            "/api/clients/geocode?q=5ta+calle+2-30", headers=admin_headers
        )
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_geocode_requires_authentication(client):
    resp = client.get("/api/clients/geocode?q=5ta+calle+2-30")
    assert resp.status_code == 401


def test_client_creation_still_requires_coordinates(client, admin_headers):
    # El geocoding es una ayuda del frontend: el contrato del backend sigue
    # exigiendo lat/lng al crear clientes.
    resp = client.post(
        "/api/clients/", json={"name": "X", "address": "Y"}, headers=admin_headers
    )
    assert resp.status_code == 422