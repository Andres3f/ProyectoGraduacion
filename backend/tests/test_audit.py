"""Tests de logs de auditoría (quién hizo qué)."""

import io
import csv


def _clients(client, admin_headers, n=1):
    ids = []
    for i in range(n):
        resp = client.post(
            "/api/clients/",
            json={
                "name": f"Audit {i}",
                "address": f"Dir {i}",
                "latitude": 14.61 + i * 0.001,
                "longitude": -89.98,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    return ids


def _setup_route(client, admin_headers):
    """Crea conductor + cliente + pedido + vehículo y optimiza una ruta."""
    resp = client.post(
        "/api/users/",
        json={
            "email": "cond.audit@optirutas.com",
            "full_name": "Conductor Audit",
            "password": "Passw0rd!",
            "role": "conductor",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    driver_id = resp.json()["id"]
    cid = _clients(client, admin_headers)[0]
    order = client.post(
        "/api/orders/", json={"client_id": cid, "weight_kg": 1000},
        headers=admin_headers,
    )
    assert order.status_code == 200, order.text
    v_resp = client.post(
        "/api/vehicles/",
        json={"plate": "A-9999", "capacity_kg": 5000, "driver_id": driver_id},
        headers=admin_headers,
    )
    assert v_resp.status_code == 200, v_resp.text
    v = v_resp.json()["id"]
    return [order.json()["id"]], [v]


def test_login_creates_audit_log(client, admin_headers):
    logs = client.get("/api/logs", headers=admin_headers).json()
    assert len(logs) >= 1
    assert any(l["accion"] == "login" for l in logs)


def test_optimize_creates_audit_log(client, admin_headers):
    order_ids, vehicle_ids = _setup_route(client, admin_headers)
    opt = client.post(
        "/api/routes/optimize",
        json={"order_ids": order_ids, "vehicle_ids": vehicle_ids},
        headers=admin_headers,
    )
    assert opt.status_code == 200, opt.text

    logs = client.get("/api/logs", headers=admin_headers).json()
    matching = [l for l in logs if l["accion"] == "optimizar_rutas"]
    assert matching, "debe existir un log de optimizar_rutas"
    assert matching[0]["detalle"]["routes_creadas"] == 1
    assert matching[0]["detalle"]["matrix_source"] in ("ors", "haversine")


def test_create_vehicle_creates_audit_log(client, admin_headers):
    resp = client.post(
        "/api/vehicles/",
        json={"plate": "A-1234", "capacity_kg": 5000},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    logs = client.get("/api/logs", headers=admin_headers).json()
    assert any(l["accion"] == "crear_vehiculo" for l in logs)


def test_upload_creates_massive_upload_log(client, admin_headers):
    cid = _clients(client, admin_headers)[0]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["client_id", "weight_kg", "volume_m3"])
    writer.writerow([cid, 200, 5])
    resp = client.post(
        "/api/orders/upload",
        files={"file": ("audit.csv", buf.getvalue().encode(), "text/csv")},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    logs = client.get("/api/logs", headers=admin_headers).json()
    up = [l for l in logs if l["accion"] == "carga_masiva_pedidos"]
    assert up, "debe existir log de carga_masiva_pedidos"
    assert up[0]["detalle"]["creados"] == 1


def test_logs_forbidden_for_non_admin(client, regular_user_headers):
    resp = client.get("/api/logs", headers=regular_user_headers)
    assert resp.status_code == 403
