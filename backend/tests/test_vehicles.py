"""Tests del CRUD de vehículos (OPT-7)."""

from app.database import SessionLocal, engine, Base
import app.models.route  # noqa: F401


def _make_driver(client, admin_headers, email="conductor.v@optirutas.com"):
    resp = client.post(
        "/api/users",
        json={
            "email": email,
            "full_name": "Conductor Vehículo",
            "password": "Passw0rd!",
            "role": "conductor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_vehicle(client, headers, **overrides):
    payload = {
        "plate": "C-1234",
        "capacity_kg": 8000,
        "capacity_m3": 15,
    }
    payload.update(overrides)
    return client.post("/api/vehicles/", json=payload, headers=headers)


def test_create_vehicle(client, admin_headers):
    resp = _make_vehicle(client, admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["plate"] == "C-1234"
    assert body["capacity_kg"] == 8000


def test_plate_normalized_uppercase(client, admin_headers):
    resp = _make_vehicle(client, admin_headers, plate="c-4567")
    assert resp.status_code == 200
    assert resp.json()["plate"] == "C-4567"


def test_create_vehicle_invalid_plate(client, admin_headers):
    resp = _make_vehicle(client, admin_headers, plate="X1-2")
    assert resp.status_code == 422


def test_create_vehicle_invalid_capacity(client, admin_headers):
    resp = _make_vehicle(client, admin_headers, capacity_kg=0)
    assert resp.status_code == 422
    resp = _make_vehicle(client, admin_headers, capacity_m3=-5)
    assert resp.status_code == 422


def test_create_vehicle_with_driver(client, admin_headers):
    driver_id = _make_driver(client, admin_headers)
    resp = _make_vehicle(client, admin_headers, driver_id=driver_id)
    assert resp.status_code == 200
    assert resp.json()["driver_id"] == driver_id


def test_create_vehicle_driver_not_conductor(client, admin_headers):
    resp = client.post(
        "/api/users",
        json={
            "email": "planificador.veh@optirutas.com",
            "full_name": "Planificador",
            "password": "Passw0rd!",
            "role": "planificador",
        },
        headers=admin_headers,
    )
    planificador_id = resp.json()["id"]
    resp = _make_vehicle(client, admin_headers, driver_id=planificador_id)
    assert resp.status_code == 400


def test_create_vehicle_driver_not_found(client, admin_headers):
    resp = _make_vehicle(client, admin_headers, driver_id=99999)
    assert resp.status_code == 400


def test_list_vehicles(client, admin_headers):
    resp = client.get("/api/vehicles/", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_vehicle_by_id(client, admin_headers):
    vehicle_id = _make_vehicle(client, admin_headers).json()["id"]
    resp = client.get(f"/api/vehicles/{vehicle_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == vehicle_id


def test_get_vehicle_not_found(client, admin_headers):
    resp = client.get("/api/vehicles/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_update_vehicle(client, admin_headers):
    vehicle_id = _make_vehicle(client, admin_headers).json()["id"]
    driver_id = _make_driver(client, admin_headers, email="conductor.upd@optirutas.com")
    resp = client.put(
        f"/api/vehicles/{vehicle_id}",
        json={"capacity_kg": 12000, "driver_id": driver_id},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["capacity_kg"] == 12000
    assert resp.json()["driver_id"] == driver_id


def test_delete_vehicle(client, admin_headers):
    vehicle_id = _make_vehicle(client, admin_headers).json()["id"]
    resp = client.delete(f"/api/vehicles/{vehicle_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert client.get(f"/api/vehicles/{vehicle_id}", headers=admin_headers).status_code == 404


def test_delete_vehicle_forbidden_non_admin(client, regular_user_headers):
    resp = client.delete("/api/vehicles/1", headers=regular_user_headers)
    assert resp.status_code == 403


def test_delete_vehicle_with_routes(client, admin_headers):
    vehicle_id = _make_vehicle(client, admin_headers).json()["id"]
    db = SessionLocal()
    try:
        from app.models.route import Route
        db.add(Route(name="Ruta ligada", vehicle_id=vehicle_id))
        db.commit()
    finally:
        db.close()
    resp = client.delete(f"/api/vehicles/{vehicle_id}", headers=admin_headers)
    assert resp.status_code == 400