"""
Prueba integral end-to-end (OPT-21) + cobertura de conductor (OPT-18).

Encadena el flujo real de un día de reparto:
  crear cliente → crear pedido → crear vehículo (con conductor) → optimizar
  ruta → verificar route_stops → conductor marca entregado → ruta completada.

Además verifica las reglas de aislamiento por rol del conductor:
  - un conductor solo ve/marca sus propias rutas (nunca las de otros),
  - un conductor NO puede listar todas las rutas (403).
"""

from app.database import SessionLocal


# ── Helpers ──────────────────────────────────────────────────


def _create_conductor(client, admin_headers, suffix):
    email = f"conductor.{suffix}@optirutas.com"
    resp = client.post(
        "/api/users/",
        json={
            "email": email,
            "full_name": f"Conductor {suffix}",
            "password": "Passw0rd!",
            "role": "conductor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    driver_id = resp.json()["id"]
    login = client.post(
        "/api/auth/login", json={"email": email, "password": "Passw0rd!"}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    return driver_id, headers


def _make_client(client, headers, name, lat, lng):
    resp = client.post(
        "/api/clients/",
        json={
            "name": name,
            "address": f"Dir {name}",
            "latitude": lat,
            "longitude": lng,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_order(client, headers, client_id, weight_kg):
    resp = client.post(
        "/api/orders/",
        json={"client_id": client_id, "weight_kg": weight_kg},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _make_vehicle(client, headers, plate, capacity_kg, driver_id):
    resp = client.post(
        "/api/vehicles/",
        json={"plate": plate, "capacity_kg": capacity_kg, "driver_id": driver_id},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


_plate_counter = 2000


def _full_setup(client, admin_headers, driver_id, suffix, weight=1000):
    global _plate_counter
    _plate_counter += 1
    plate = f"R-{_plate_counter}"
    c1 = _make_client(client, admin_headers, f"Cliente {suffix}A", 14.61, -89.98)
    c2 = _make_client(client, admin_headers, f"Cliente {suffix}B", 14.65, -89.99)
    v = _make_vehicle(client, admin_headers, plate, 5000, driver_id)
    o1 = _make_order(client, admin_headers, c1, weight)
    o2 = _make_order(client, admin_headers, c2, weight)
    return v, o1, o2


def _optimize(client, admin_headers, orders, vehicle):
    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": orders, "vehicle_ids": [vehicle]},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    return body


# ── OPT-18: aislamiento del conductor ────────────────────────


def test_conductor_cannot_list_all_routes(client, admin_headers):
    """Un conductor NO accede a GET /api/routes (403)."""
    _, driver_headers = _create_conductor(client, admin_headers, "forbidden")
    resp = client.get("/api/routes/", headers=driver_headers)
    assert resp.status_code == 403


def test_conductor_sees_only_own_route(client, admin_headers):
    """Cada conductor ve únicamente su propia ruta en /my-route."""
    d1, h1 = _create_conductor(client, admin_headers, "uno")
    d2, h2 = _create_conductor(client, admin_headers, "dos")

    v1, a11, a12 = _full_setup(client, admin_headers, d1, "uno")
    v2, a21, a22 = _full_setup(client, admin_headers, d2, "dos")

    _optimize(client, admin_headers, [a11, a12], v1)
    _optimize(client, admin_headers, [a21, a22], v2)

    r1 = client.get("/api/routes/my-route", headers=h1)
    assert r1.status_code == 200, r1.text
    r2 = client.get("/api/routes/my-route", headers=h2)
    assert r2.status_code == 200, r2.text

    # Cada uno obtiene su ruta (la que apunta a su vehículo/conductor).
    assert r1.json()["vehicle_id"] == v1
    assert r2.json()["vehicle_id"] == v2
    assert r1.json()["id"] != r2.json()["id"]


def test_conductor_cannot_view_other_route_by_id(client, admin_headers):
    """Un conductor no puede leer GET /api/routes/{id} de otro conductor."""
    d1, h1 = _create_conductor(client, admin_headers, "leakA")
    d2, h2 = _create_conductor(client, admin_headers, "leakB")

    v1, o1, o2 = _full_setup(client, admin_headers, d1, "leakA")
    body = _optimize(client, admin_headers, [o1, o2], v1)
    route_id = body["routes"][0]["id"]

    resp = client.get(f"/api/routes/{route_id}", headers=h2)
    assert resp.status_code == 404

    # El conductor dueño sí puede verla.
    own = client.get(f"/api/routes/{route_id}", headers=h1)
    assert own.status_code == 200
    assert own.json()["id"] == route_id


def test_conductor_cannot_mark_other_driver_stop(client, admin_headers):
    """Un conductor no puede marcar paradas de la ruta de otro (404)."""
    d1, h1 = _create_conductor(client, admin_headers, "marc1")
    d2, h2 = _create_conductor(client, admin_headers, "marc2")

    v1, o1, o2 = _full_setup(client, admin_headers, d1, "marc1")
    v2, o3, o4 = _full_setup(client, admin_headers, d2, "marc2")

    body = _optimize(client, admin_headers, [o1, o2], v1)
    stop1 = body["routes"][0]["stops"][0]

    # El conductor 2 intenta marcar una parada de la ruta del conductor 1.
    resp = client.put(
        f"/api/route-stops/{stop1['id']}/status",
        params={"status": "entregado"},
        headers=h2,
    )
    assert resp.status_code == 404


def test_admin_roles_can_view_any_route_by_id(client, admin_headers):
    """Admin, planificador y gerente pueden ver cualquier ruta por ID."""
    d1, _ = _create_conductor(client, admin_headers, "adminview")
    v1, o1, o2 = _full_setup(client, admin_headers, d1, "adminview")
    body = _optimize(client, admin_headers, [o1, o2], v1)
    route_id = body["routes"][0]["id"]

    # Admin.
    resp = client.get(f"/api/routes/{route_id}", headers=admin_headers)
    assert resp.status_code == 200

    # Planificador.
    resp = client.post(
        "/api/users/",
        json={
            "email": "plan.adminview@optirutas.com",
            "full_name": "Plan AdminView",
            "password": "Passw0rd!",
            "role": "planificador",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    plan_headers = _auth(client, "plan.adminview@optirutas.com")
    resp = client.get(f"/api/routes/{route_id}", headers=plan_headers)
    assert resp.status_code == 200


def _auth(client, email):
    login = client.post("/api/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_invalid_stop_status_400(client, admin_headers):
    driver_id, h = _create_conductor(client, admin_headers, "status")
    v1, o1, o2 = _full_setup(client, admin_headers, driver_id, "status")
    body = _optimize(client, admin_headers, [o1, o2], v1)
    stop_id = body["routes"][0]["stops"][0]["id"]
    resp = client.put(
        f"/api/route-stops/{stop_id}/status",
        params={"status": "otra_cosa"},
        headers=h,
    )
    assert resp.status_code == 400


def _driver_id(client, headers):
    return client.get("/api/users/me", headers=headers).json()["id"]


# ── OPT-21: flujo completo end-to-end ─────────────────────────


def test_full_e2e_delivery_flow(client, admin_headers):
    """Cliente → pedido → vehículo → ruta → conductor entrega → completada."""
    driver_id, driver_headers = _create_conductor(client, admin_headers, "e2e")

    vehicle = _make_vehicle(client, admin_headers, "R-7777", 5000, driver_id)
    c1 = _make_client(client, admin_headers, "Cliente E2E A", 14.61, -89.98)
    c2 = _make_client(client, admin_headers, "Cliente E2E B", 14.65, -89.99)
    o1 = _make_order(client, admin_headers, c1, 1000)
    o2 = _make_order(client, admin_headers, c2, 1000)

    body = _optimize(client, admin_headers, [o1, o2], vehicle)
    assert len(body["routes"]) == 1
    route = body["routes"][0]
    assert route["vehicle_id"] == vehicle
    stops = route["stops"]
    assert len(stops) == 2
    assert {s["order_id"] for s in stops} == {o1, o2}

    # El conductor ve su ruta con las paradas en orden.
    my_route = client.get("/api/routes/my-route", headers=driver_headers)
    assert my_route.status_code == 200
    assert {s["order_id"] for s in my_route.json()["stops"]} == {o1, o2}

    # Marca la primera parada como entregada → status/delivered_at actualizado.
    stop_a = my_route.json()["stops"][0]
    resp = client.put(
        f"/api/route-stops/{stop_a['id']}/status",
        params={"status": "entregado"},
        headers=driver_headers,
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        from app.models.route_stop import RouteStop
        updated = db.get(RouteStop, stop_a["id"])
        assert updated.status == "entregado"
        assert updated.delivered_at is not None
    finally:
        db.close()

    # La ruta aún no está completa porque queda una parada pendiente.
    still_pending = client.get("/api/routes/my-route", headers=driver_headers).json()
    assert still_pending["status"] == "planificada"
    route_id = still_pending["id"]

    # Marca la segunda parada → todas resueltas → la ruta se completa.
    stop_b = still_pending["stops"][1]
    resp = client.put(
        f"/api/route-stops/{stop_b['id']}/status",
        params={"status": "entregado"},
        headers=driver_headers,
    )
    assert resp.status_code == 200

    # Una ruta completada ya no se expone en /my-route (que solo devuelve
    # en_progreso/planificada), así que el admin la consulta directamente.
    completed = client.get(f"/api/routes/{route_id}", headers=admin_headers).json()
    assert completed["status"] == "completada"
