"""Tests del endpoint compartido de geocoding (/api/geocode)."""

from unittest.mock import patch

from app.services.ors_client import ORSError

MOCK_CANDIDATES = [
    {"label": "5ta Calle 2-30, Zona 1, Jalapa, Guatemala", "lat": 14.6350,
     "lng": -89.9880, "confidence": 0.9, "source": "ors"},
    {"label": "5a Avenida 2-30, Jalapa, Guatemala", "lat": 14.6310,
     "lng": -89.9920, "confidence": 0.6, "source": "ors"},
]


def test_geocode_returns_candidates(client, admin_headers):
    # Mockea el proveedor: nunca llamar a ORS/Nominatim real en los tests.
    with patch("app.routers.geocoding.geocode_address", return_value=MOCK_CANDIDATES):
        resp = client.get(
            "/api/geocode?q=5ta+calle+2-30", headers=admin_headers
        )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[0]["lat"] == 14.6350
    assert results[0]["source"] == "ors"


def test_geocode_rejects_too_short_query(client, admin_headers):
    resp = client.get("/api/geocode?q=ab", headers=admin_headers)
    assert resp.status_code == 400


def test_geocode_returns_empty_list_when_both_providers_fail(
    client, admin_headers
):
    # ORS y Nominatim caídos → la API responde 200 con [], no un 500.
    with patch(
        "app.routers.geocoding.geocode_address",
        side_effect=ORSError("ambos proveedores caídos"),
    ):
        resp = client.get(
            "/api/geocode?q=5ta+calle+2-30", headers=admin_headers
        )
    assert resp.status_code == 200
    assert resp.json()["results"] == []


def test_geocode_requires_authentication(client):
    resp = client.get("/api/geocode?q=5ta+calle+2-30")
    assert resp.status_code == 401