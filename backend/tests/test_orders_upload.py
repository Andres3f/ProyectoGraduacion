"""Tests de carga masiva de pedidos CSV/Excel (OPT-9)."""

import io
import csv


def _make_clients(client, admin_headers, n=2):
    ids = []
    for i in range(n):
        resp = client.post(
            "/api/clients/",
            json={
                "name": f"Masivo {i}",
                "address": f"Dirección {i}, Jalapa",
                "zone": "Centro",
                "latitude": 14.63 + i * 0.001,
                "longitude": -89.99,
            },
            headers=admin_headers,
        )
        assert resp.status_code == 201, resp.text
        ids.append(resp.json()["id"])
    return ids


def _csv_bytes(rows, cols=("client_id", "weight_kg", "volume_m3")):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(cols)
    writer.writerows(rows)
    return buf.getvalue().encode()


def _upload(client, headers, content, filename="pedidos.csv"):
    return client.post(
        "/api/orders/upload",
        files={"file": (filename, content, "text/csv")},
        headers=headers,
    )


def test_upload_valid_csv(client, admin_headers):
    ids = _make_clients(client, admin_headers)
    csv_bytes = _csv_bytes(
        [(ids[0], 500, 10), (ids[1], 750, 12.5)]
    )
    resp = _upload(client, admin_headers, csv_bytes)
    assert resp.status_code == 200
    assert resp.json() == {"created": 2}
    orders = client.get("/api/orders/", headers=admin_headers).json()
    assert len(orders) == 2
    # El pedido trae el snapshot denormalizado del cliente
    assert orders[0]["client_name"] == "Masivo 0"
    assert orders[0]["client_id"] == ids[0]


def test_upload_missing_columns(client, admin_headers):
    _make_clients(client, admin_headers)
    csv_bytes = _csv_bytes([(1, 500, 10)], cols=("client_id", "weight_kg"))
    resp = _upload(client, admin_headers, csv_bytes)
    assert resp.status_code == 400
    assert "Faltan columnas" in resp.json()["detail"]


def test_upload_invalid_format(client, admin_headers):
    resp = _upload(client, admin_headers, b"datos", filename="pedidos.txt")
    assert resp.status_code == 400


def test_upload_nonexistent_client_is_atomic(client, admin_headers):
    ids = _make_clients(client, admin_headers, n=1)
    # Fila 1 válida, fila 2 con cliente inexistente → error y NO crea nada
    csv_bytes = _csv_bytes([(ids[0], 500, 10), (99999, 300, 5)])
    resp = _upload(client, admin_headers, csv_bytes)
    assert resp.status_code == 400
    assert "errors" in resp.json()["detail"]
    orders = client.get("/api/orders/", headers=admin_headers).json()
    assert len(orders) == 0


def test_upload_negative_weight(client, admin_headers):
    ids = _make_clients(client, admin_headers, n=1)
    csv_bytes = _csv_bytes([(ids[0], -100, 10)])
    resp = _upload(client, admin_headers, csv_bytes)
    assert resp.status_code == 400


def test_upload_xlsx(client, admin_headers):
    import openpyxl

    ids = _make_clients(client, admin_headers, n=1)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["client_id", "weight_kg", "volume_m3"])
    ws.append([ids[0], 420, 9])
    buf = io.BytesIO()
    wb.save(buf)
    resp = _upload(client, admin_headers, buf.getvalue(), filename="pedidos.xlsx")
    assert resp.status_code == 200
    assert resp.json() == {"created": 1}