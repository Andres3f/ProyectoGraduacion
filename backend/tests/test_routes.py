"""Tests del endpoint de optimización de rutas (OPT-11) y persistencia (OPT-13)."""

from app.database import SessionLocal


def _make_client(client, headers, name, lat, lng):
    resp = client.post(
        "/api/clients/",
        json={"name": name, "address": f"Dir {name}", "latitude": lat, "longitude": lng},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_order(client, headers, client_id, weight_kg, time_window=None):
    payload = {"client_id": client_id, "weight_kg": weight_kg}
    if time_window:
        payload["time_window_start"] = time_window[0]
        payload["time_window_end"] = time_window[1]
    resp = client.post("/api/orders/", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _make_vehicle(client, headers, plate, capacity_kg, active=True):
    resp = client.post(
        "/api/vehicles/",
        json={"plate": plate, "capacity_kg": capacity_kg},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    vid = resp.json()["id"]
    if not active:
        db = SessionLocal()
        try:
            from app.models.vehicle import Vehicle
            v = db.get(Vehicle, vid)
            v.is_active = False
            db.commit()
        finally:
            db.close()
    return vid


def _setup(client, headers):
    """Crea clientes + vehículos y devuelve ids útiles."""
    c1 = _make_client(client, headers, "Cliente 1", 14.61, -89.98)
    c2 = _make_client(client, headers, "Cliente 2", 14.65, -89.99)
    c3 = _make_client(client, headers, "Cliente 3", 14.62, -89.97)
    v1 = _make_vehicle(client, headers, "R-1001", 3000)
    v2 = _make_vehicle(client, headers, "R-1002", 3000)
    return c1, c2, c3, v1, v2


def test_optimize_success_single_vehicle(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    o1 = _make_order(client, admin_headers, c1, 1000)
    o2 = _make_order(client, admin_headers, c2, 500)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1, o2], "vehicle_ids": [v1]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["unassigned_order_ids"] == []
    assert len(body["routes"]) == 1
    assert body["routes"][0]["vehicle_id"] == v1
    # Métricas presentes
    assert "metrics" in body
    assert "reduction_percentage" in body["metrics"]


def test_optimize_success_two_vehicles(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    # Peso total > capacidad de un solo vehículo (3000) pero cabe en dos.
    o1 = _make_order(client, admin_headers, c1, 2000)
    o2 = _make_order(client, admin_headers, c2, 2000)
    o3 = _make_order(client, admin_headers, c3, 2000)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1, o2, o3], "vehicle_ids": [v1, v2]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert len(body["routes"]) == 2, "se deben crear dos rutas"
    vehicle_ids = {r["vehicle_id"] for r in body["routes"]}
    assert vehicle_ids == {v1, v2}


def test_optimize_unassigned_orders_returns_200(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    # Peso (5000) excede la capacidad de todos los vehículos disponibles.
    o1 = _make_order(client, admin_headers, c1, 5000)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1], "vehicle_ids": [v1]},
        headers=admin_headers,
    )
    # No debe ser un 500: el usuario debe ver qué quedó sin asignar.
    assert resp.status_code == 200
    body = resp.json()
    assert o1 in body["unassigned_order_ids"]


def test_optimize_vehicle_not_found_400(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    o1 = _make_order(client, admin_headers, c1, 1000)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1], "vehicle_ids": [99999]},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_optimize_inactive_vehicle_400(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    o1 = _make_order(client, admin_headers, c1, 1000)
    v1 = _make_vehicle(client, admin_headers, "R-2001", 3000, active=False)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1], "vehicle_ids": [v1]},
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_optimize_forbidden_non_planner(client, regular_user_headers):
    # La validación de rol ocurre antes de consultar la BD: basta un payload
    # cualquiera para comprobar el 403.
    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [1], "vehicle_ids": [1]},
        headers=regular_user_headers,
    )
    assert resp.status_code == 403


def test_optimize_creates_routestops_and_sets_en_ruta(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    o1 = _make_order(client, admin_headers, c1, 1000)
    o2 = _make_order(client, admin_headers, c2, 2000)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1, o2], "vehicle_ids": [v1]},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    route = body["routes"][0]
    assert route["vehicle_id"] == v1

    stops = route["stops"]
    assert len(stops) == 2
    # Secuencia correcta y continua
    assert sorted(s["sequence"] for s in stops) == [0, 1]
    assert sorted(s["order_id"] for s in stops) == [o1, o2]

    # Los pedidos pasan a estado "en_ruta"
    for oid in [o1, o2]:
        o = client.get(f"/api/orders/{oid}", headers=admin_headers).json()
        assert o["status"] == "en_ruta"


def test_get_route_returns_stops_from_relation(client, admin_headers):
    c1, c2, c3, v1, v2 = _setup(client, admin_headers)
    o1 = _make_order(client, admin_headers, c1, 1000)
    o2 = _make_order(client, admin_headers, c2, 2000)

    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1, o2], "vehicle_ids": [v1]},
        headers=admin_headers,
    )
    rid = resp.json()["routes"][0]["id"]

    details = client.get(f"/api/routes/{rid}", headers=admin_headers)
    assert details.status_code == 200
    stops = details.json()["stops"]
    assert len(stops) == 2
    assert all(isinstance(s["sequence"], int) for s in stops)
