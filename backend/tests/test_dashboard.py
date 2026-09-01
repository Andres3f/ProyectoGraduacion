"""Tests del dashboard de KPIs (OPT-22) y exportación de reportes (OPT-23)."""

from datetime import date, datetime, timedelta

from app.database import SessionLocal


def _auth_headers(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_conductor(client, admin_headers):
    resp = client.post(
        "/api/users/",
        json={
            "email": "cond.dash@optirutas.com",
            "full_name": "Conductor Dash",
            "password": "Passw0rd!",
            "role": "conductor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_client(client, headers, name, lat, lng):
    resp = client.post(
        "/api/clients/",
        json={"name": name, "address": f"Dir {name}", "latitude": lat, "longitude": lng},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _make_order(client, headers, client_id, weight_kg):
    resp = client.post(
        "/api/orders/", json={"client_id": client_id, "weight_kg": weight_kg},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _setup_route(client, admin_headers):
    """Crea cliente+pedido+vehículo y optimiza una ruta de 1 parada."""
    driver_id = _create_conductor(client, admin_headers)
    c1 = _make_client(client, admin_headers, "Dash Cliente", 14.61, -89.98)
    o1 = _make_order(client, admin_headers, c1, 1000)
    v_resp = client.post(
        "/api/vehicles/",
        json={"plate": "R-7777", "capacity_kg": 5000, "driver_id": driver_id},
        headers=admin_headers,
    )
    assert v_resp.status_code == 200, v_resp.text
    v = v_resp.json()["id"]
    opt = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1], "vehicle_ids": [v]},
        headers=admin_headers,
    )
    assert opt.status_code == 200, opt.text
    route = opt.json()["routes"][0]
    return route


# ── OPT-22: KPIs ──────────────────────────────────────────────


def test_kpis_with_routes(client, admin_headers):
    route = _setup_route(client, admin_headers)
    stop_id = route["stops"][0]["id"]

    # Marca la parada como entregada a tiempo (delivered_at <= eta).
    db = SessionLocal()
    try:
        from app.models.route_stop import RouteStop
        stop = db.get(RouteStop, stop_id)
        stop.status = "entregado"
        stop.delivered_at = stop.eta or datetime.utcnow()
        db.commit()
    finally:
        db.close()

    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis",
        params={
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=1)).isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    k = resp.json()
    assert k["total_routes"] == 1
    assert k["total_distance_km"] > 0
    assert k["delivery_rate_pct"] == 100.0
    assert k["on_time_rate_pct"] == 100.0
    assert k["avg_km_per_route"] > 0
    # PG-22: KPIs de ahorro presentes y no negativos.
    assert "fuel_liters_saved" in k and k["fuel_liters_saved"] >= 0
    assert "operational_cost_saved_gtq" in k and k["operational_cost_saved_gtq"] >= 0
    assert "fuel_cost_saved_gtq" in k and k["fuel_cost_saved_gtq"] >= 0
    # PG-23: distribución de entregas.
    assert k["delivery_distribution"] == {
        "entregado": 1, "fallido": 0, "pendiente": 0,
    }


def test_kpis_empty_no_division_by_zero(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis",
        params={
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": (today - timedelta(days=29)).isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    k = resp.json()
    assert k == {
        "total_distance_km": 0,
        "total_routes": 0,
        "delivery_rate_pct": 0,
        "on_time_rate_pct": 0,
        "avg_km_per_route": 0,
        "fuel_liters_saved": 0,
        "fuel_cost_saved_gtq": 0,
        "operational_cost_saved_gtq": 0,
        "delivery_distribution": {"entregado": 0, "fallido": 0, "pendiente": 0},
    }


def test_kpis_requires_gerente_or_admin(client, admin_headers):
    # Un planificador no debe acceder al dashboard de gerente.
    resp = client.post(
        "/api/users/",
        json={
            "email": "plan.dash@optirutas.com",
            "full_name": "Plan Dash",
            "password": "Passw0rd!",
            "role": "planificador",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    plan_headers = _auth_headers(client, "plan.dash@optirutas.com", "Passw0rd!")
    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=plan_headers,
    )
    assert resp.status_code == 403


# ── PG-23: serie temporal (línea) ────────────────────────────


def _auth_headers(client, email, password):
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_timeseries_with_routes_by_day(client, admin_headers):
    # Crea una ruta de 2 paradas en ubicaciones separadas para que exista
    # reducción (antes vs después no son iguales).
    driver_id = _create_conductor(client, admin_headers)
    c1 = _make_client(client, admin_headers, "TS Cliente A", 14.61, -89.98)
    c2 = _make_client(client, admin_headers, "TS Cliente B", 14.70, -89.90)
    o1 = _make_order(client, admin_headers, c1, 500)
    o2 = _make_order(client, admin_headers, c2, 500)
    v_resp = client.post(
        "/api/vehicles/",
        json={"plate": "R-8888", "capacity_kg": 5000, "driver_id": driver_id},
        headers=admin_headers,
    )
    assert v_resp.status_code == 200, v_resp.text
    v = v_resp.json()["id"]
    opt = client.post(
        "/api/routes/optimize",
        json={"order_ids": [o1, o2], "vehicle_ids": [v]},
        headers=admin_headers,
    )
    assert opt.status_code == 200, opt.text
    route_id = opt.json()["routes"][0]["id"]

    # Pone la ruta en el día de ayer para generar una serie con un punto.
    db = SessionLocal()
    try:
        from app.models.route import Route
        r = db.get(Route, route_id)
        r.created_at = datetime.utcnow() - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis/timeseries",
        params={
            "date_from": (today - timedelta(days=2)).isoformat(),
            "date_to": today.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["series"]) == 1
    assert "reduction_percentage" in body["series"][0]
    assert body["series"][0]["reduction_percentage"] >= 0
    assert body["series"][0]["km_saved"] >= 0


def test_timeseries_empty_no_error(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis/timeseries",
        params={
            "date_from": (today - timedelta(days=30)).isoformat(),
            "date_to": (today - timedelta(days=29)).isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["series"] == []


def test_timeseries_requires_admin_or_gerente(client, admin_headers):
    resp = client.post(
        "/api/users/",
        json={
            "email": "plan.ts@optirutas.com",
            "full_name": "Plan TS",
            "password": "Passw0rd!",
            "role": "planificador",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    plan_headers = _auth_headers(client, "plan.ts@optirutas.com", "Passw0rd!")
    today = date.today()
    resp = client.get(
        "/api/dashboard/kpis/timeseries",
        params={"date_from": today.isoformat(), "date_to": today.isoformat()},
        headers=plan_headers,
    )
    assert resp.status_code == 403


# ── OPT-23: exportación ───────────────────────────────────────


def test_export_xlsx(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/api/dashboard/export",
        params={
            "format": "xlsx",
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=1)).isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]
    assert len(resp.content) > 0
    assert "attachment" in resp.headers["content-disposition"]


def test_export_pdf(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/api/dashboard/export",
        params={
            "format": "pdf",
            "date_from": (today - timedelta(days=1)).isoformat(),
            "date_to": (today + timedelta(days=1)).isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert len(resp.content) > 0
    assert "attachment" in resp.headers["content-disposition"]


def test_export_invalid_format_400(client, admin_headers):
    today = date.today()
    resp = client.get(
        "/api/dashboard/export",
        params={
            "format": "csv",
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
