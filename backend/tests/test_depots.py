"""Tests del CRUD de depósitos / punto de partida (feature/depositos-mapa).

Regla de negocio clave: siempre debe existir exactamente un depósito con
``is_default = True``; el default no se puede eliminar y no se puede borrar un
depósito con vehículos asignados.
"""


def _make_depot(client, headers, **overrides):
    payload = {
        "name": "Bodega Centro",
        "address": "1 Avenida 9-28, Zona 1, Jalapa",
        "latitude": 14.6347,
        "longitude": -89.9889,
    }
    payload.update(overrides)
    return client.post("/api/depots/", json=payload, headers=headers)


def test_create_depot_and_single_default_rule(client, admin_headers):
    # Al crear un depósito con is_default=True, el anterior deja de serlo.
    with_default = _make_depot(client, admin_headers, name="Nuevo Patio", is_default=True)
    assert with_default.status_code == 201
    assert with_default.json()["is_default"] is True

    resp = client.get("/api/depots/", headers=admin_headers)
    depots = resp.json()
    assert len(depots) == 2  # el default del conftest + el nuevo
    assert sum(d["is_default"] for d in depots) == 1, "exactamente un default"


def test_set_default_depot_only_one(client, admin_headers):
    created = _make_depot(client, admin_headers, name="Patio Norte")
    depot_id = created.json()["id"]

    resp = client.put(f"/api/depots/{depot_id}/set-default", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["is_default"] is True

    depots = client.get("/api/depots/", headers=admin_headers).json()
    assert sum(d["is_default"] for d in depots) == 1


def test_delete_default_depot_blocked(client, admin_headers):
    depots = client.get("/api/depots/", headers=admin_headers).json()
    default = next(d for d in depots if d["is_default"])

    resp = client.delete(f"/api/depots/{default['id']}", headers=admin_headers)
    assert resp.status_code == 400
    assert "predeterminado" in resp.json()["detail"].lower()


def test_delete_depot_with_assigned_vehicles_blocked(client, admin_headers):
    # Primero se necesita un depósito no-default y un vehículo con depot_id.
    resp = _make_depot(client, admin_headers, name="Patio Viejo")
    depot_id = resp.json()["id"]
    vresp = client.post(
        "/api/vehicles/",
        json={
            "plate": "P-777",
            "description": "Camión del patio viejo",
            "capacity_kg": 5000,
            "capacity_m3": 20,
            "depot_id": depot_id,
        },
        headers=admin_headers,
    )
    assert vresp.status_code == 200, vresp.text
    assert vresp.json()["depot_id"] == depot_id

    resp = client.delete(f"/api/depots/{depot_id}", headers=admin_headers)
    assert resp.status_code == 400
    assert "vehículos" in resp.json()["detail"].lower()


def test_delete_non_default_depot_without_vehicles(client, admin_headers):
    created = _make_depot(client, admin_headers, name="Patio Temporal")
    depot_id = created.json()["id"]

    resp = client.delete(f"/api/depots/{depot_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Depósito eliminado"


def test_update_depot(client, admin_headers):
    created = _make_depot(client, admin_headers, name="Patio A")
    depot_id = created.json()["id"]

    resp = client.put(
        f"/api/depots/{depot_id}",
        json={"name": "Patio A Renombrado", "latitude": 14.62},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Patio A Renombrado"
    assert body["latitude"] == 14.62


def test_depot_writes_admin_only(client, admin_headers, planner_headers):
    # El planificador puede leer depósitos, pero no crearlos ni borrarlos.
    resp = _make_depot(client, planner_headers, name="Patio Prohibido")
    assert resp.status_code == 403

    depots = client.get("/api/depots/", headers=planner_headers)
    assert depots.status_code == 200

    listed = client.get("/api/depots/", headers=admin_headers).json()
    resp = client.delete(
        f"/api/depots/{listed[0]['id']}", headers=planner_headers
    )
    assert resp.status_code == 403


def test_list_depots_requires_authentication(client):
    resp = client.get("/api/depots/")
    assert resp.status_code == 401