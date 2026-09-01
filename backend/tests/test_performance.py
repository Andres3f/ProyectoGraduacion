"""
Pruebas de rendimiento del solver (PG-25).

Miden el tiempo real que tarda el endpoint de optimización con 50 y 100
pedidos, para verificar que cumple el objetivo de <5s para 50 pedidos.

Se marcan con @pytest.mark.performance y se EXCLUYEN de la corrida normal de
tests (ver `addopts = -m "not performance"` en pytest.ini). Para ejecutarlas
localmente:

    pytest tests/test_performance.py -m performance
"""

import time

import pytest

from app.database import SessionLocal
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.user import User



def _seed_orders(n_orders: int) -> list:
    """Crea `n_orders` clientes+pedidos dispersos alrededor de Jalapa."""
    db = SessionLocal()
    order_ids = []
    try:
        admin = db.query(User).filter(User.email == "admin@optirutas.com").first()
        import math
        for i in range(n_orders):
            angle = (i * 137.5) % 360  # espiral de Fermat para dispersión
            radius = 0.01 + (i % 20) * 0.02
            lat = 14.6347 + radius * math.cos(math.radians(angle))
            lng = -89.9889 + radius * math.sin(math.radians(angle))
            c = Client(
                name=f"Cliente P{i}",
                address=f"Dir P{i}",
                latitude=round(lat, 6),
                longitude=round(lng, 6),
            )
            db.add(c)
            db.flush()
            o = Order(
                client_id=c.id,
                client_name=c.name,
                address=c.address,
                latitude=round(lat, 6),
                longitude=round(lng, 6),
                weight_kg=100.0 + (i % 40) * 25,  # 100–1075 kg, ~dist. razonable
                status=OrderStatus.pendiente,
                service_time_min=15,
                created_by=admin.id if admin else None,
            )
            db.add(o)
            db.flush()
            order_ids.append(o.id)
        db.commit()
    finally:
        db.close()
    return order_ids


def _create_vehicles(client, admin_headers, n_vehicles):
    """Crea n vehículos vía API y devuelve sus ids."""
    ids = []
    for i in range(n_vehicles):
        resp = client.post(
            "/api/vehicles/",
            json={"plate": f"PR-{i:04d}", "capacity_kg": 5000},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        ids.append(resp.json()["id"])
    return ids


@pytest.mark.performance
def test_solver_50_orders_under_5s(client, admin_headers):
    """50 pedidos + 5 vehículos deben resolverse en menos de 5 segundos."""
    order_ids = _seed_orders(50)
    vehicle_ids = _create_vehicles(client, admin_headers, 5)

    start = time.time()
    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": order_ids, "vehicle_ids": vehicle_ids},
        headers=admin_headers,
    )
    elapsed = time.time() - start

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    assert elapsed < 5.0, f"Tardó {elapsed:.2f}s para 50 pedidos (límite: 5s)"


@pytest.mark.performance
def test_solver_100_orders_10_vehicles(client, admin_headers):
    """100 pedidos + 10 vehículos: verifica que no se cuelgue."""
    order_ids = _seed_orders(100)
    vehicle_ids = _create_vehicles(client, admin_headers, 10)

    start = time.time()
    resp = client.post(
        "/api/routes/optimize",
        json={"order_ids": order_ids, "vehicle_ids": vehicle_ids},
        headers=admin_headers,
    )
    elapsed = time.time() - start

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True, body
    assert elapsed < 12.0, f"Tardó {elapsed:.2f}s para 100 pedidos"
