"""Tests del motor de optimización VRP (OPT-10)."""

from unittest.mock import patch

from app.services.optimizer import optimize_routes
from app.services.metrics import compare_before_after
from app.services.ors_client import ORSError


class _Order:
    """Stub mínimo de Order para pruebas sin base de datos."""

    def __init__(self, id, lat, lng, weight_kg, time_window=None, service_time_min=10):
        self.id = id
        self.latitude = lat
        self.longitude = lng
        self.weight_kg = weight_kg
        self.time_window_start = time_window[0] if time_window else None
        self.time_window_end = time_window[1] if time_window else None
        self.service_time_min = service_time_min
        self.client_name = f"Cliente {id}"


class _Vehicle:
    def __init__(self, id, capacity_kg):
        self.id = id
        self.capacity_kg = capacity_kg


def _orders(*specs):
    return [
        _Order(i + 1, lat, lng, weight, tw, svc)
        for i, (lat, lng, weight, tw, svc) in enumerate(specs)
    ]


def test_single_vehicle_orders_fit():
    orders = _orders(
        (14.61, -89.98, 1000, None, 10),
        (14.65, -89.99, 2000, None, 15),
        (14.62, -89.97, 500, None, 10),
    )
    vehicles = [_Vehicle(1, 10000)]

    result = optimize_routes(orders, vehicles)

    assert result["success"] is True
    assert len(result["routes"]) == 1
    assert result["unassigned_order_ids"] == []
    route = result["routes"][0]
    assert route["vehicle_id"] == 1
    assert route["total_weight_kg"] == 3500
    stop_ids = [s["order_id"] for s in route["stops"]]
    assert sorted(stop_ids) == [1, 2, 3]
    # Secuencia única y completa
    assert sorted(s["sequence"] for s in route["stops"]) == [0, 1, 2]


def test_exceeds_capacity_all_vehicles_unassigned():
    orders = _orders(
        (14.61, -89.98, 1000, None, 10),
        (14.65, -89.99, 2000, None, 10),
        (14.62, -89.97, 2500, None, 10),
    )
    vehicles = [_Vehicle(1, 3000)]

    result = optimize_routes(orders, vehicles)

    assert result["success"] is True
    assert result["unassigned_order_ids"], "debe reportar pedidos sin asignar"
    # No debe lanzarse excepción y el total asignado no excede capacidad.
    for route in result["routes"]:
        assert route["total_weight_kg"] <= 3000


def test_two_vehicles_both_receive_stops():
    orders = _orders(
        (14.61, -89.98, 1000, None, 10),
        (14.65, -89.99, 2000, None, 10),
        (14.62, -89.97, 1000, None, 10),
        (14.64, -89.96, 1000, None, 10),
    )
    vehicles = [_Vehicle(1, 3000), _Vehicle(2, 3000)]

    result = optimize_routes(orders, vehicles)

    assert result["success"] is True
    assert len(result["routes"]) == 2, "ambos vehículos deben recibir paradas"
    for route in result["routes"]:
        assert route["stops"], "cada ruta debe tener al menos una parada"
        assert route["total_weight_kg"] <= 3000


def test_impossible_time_window_marked_unassigned():
    # Pedido 1 tiene una ventana de 5 minutos muy improbable de cumplir
    # desde el deposito; el resto es razonable.
    orders = _orders(
        (14.61, -89.98, 1000, (0, 5), 10),
        (14.65, -89.99, 1000, None, 10),
        (14.62, -89.97, 1000, None, 10),
    )
    vehicles = [_Vehicle(1, 10000)]

    result = optimize_routes(orders, vehicles)

    assert result["success"] is True
    assert 1 in result["unassigned_order_ids"]
    # El resto de la ruta no se rompe: los pedidos 2 y 3 sí se asignan.
    assigned = [
        s["order_id"]
        for route in result["routes"]
        for s in route["stops"]
    ]
    assert 2 in assigned and 3 in assigned


def test_metrics_reduction_non_negative_when_optimized_shorter():
    # Pedidos en orden absurdo (alineados) para que la optimización redunde
    # en una ruta claramente más corta que el recorrido ida-y-vuelta original.
    orders = _orders(
        (14.6400, -89.9800, 100, None, 0),
        (14.6450, -89.9800, 100, None, 0),
        (14.6500, -89.9800, 100, None, 0),
        (14.6550, -89.9800, 100, None, 0),
        (14.6600, -89.9800, 100, None, 0),
    )
    vehicles = [_Vehicle(1, 1000)]

    result = optimize_routes(orders, vehicles)
    assert result["success"] is True

    optimized_stops = [s for route in result["routes"] for s in route["stops"]]
    metrics = compare_before_after(orders, optimized_stops)

    assert metrics["reduction_percentage"] >= 0
    assert metrics["distance_before_km"] > 0
    assert "estimated_fuel_savings_gtq" in metrics


def test_no_vehicles_returns_error():
    orders = _orders((14.61, -89.98, 1000, None, 10))
    result = optimize_routes(orders, [])
    assert result["success"] is False
    assert result["unassigned_order_ids"] == [1]


def test_defaults_to_haversine_when_no_ors_key():
    # Sin ORS_API_KEY configurada, el optimizer debe usar Haversine sin fallar.
    orders = _orders(
        (14.61, -89.98, 500, None, 10),
        (14.65, -89.99, 500, None, 10),
    )
    vehicles = [_Vehicle(1, 1000)]
    with patch("app.services.optimizer.settings.ORS_API_KEY", ""):
        result = optimize_routes(orders, vehicles)
    assert result["success"] is True
    assert result["matrix_source"] == "haversine"


def test_fallback_to_haversine_when_ors_errors():
    # Si ORS lanza un error, la optimización NO debe romperse: cae a Haversine.
    orders = _orders(
        (14.61, -89.98, 500, None, 10),
        (14.65, -89.99, 500, None, 10),
    )
    vehicles = [_Vehicle(1, 1000)]
    with patch(
        "app.services.optimizer.get_distance_duration_matrix",
        side_effect=ORSError("boom"),
    ):
        result = optimize_routes(orders, vehicles)
    assert result["success"] is True
    assert result["matrix_source"] == "haversine"
    assert len(result["routes"]) == 1


def test_uses_ors_matrix_when_available():
    # Si ORS responde una matriz, se usa y el fallback no interviene.
    orders = _orders(
        (14.61, -89.98, 500, None, 10),
        (14.65, -89.99, 500, None, 10),
    )
    vehicles = [_Vehicle(1, 1000)]
    n = len(orders) + 1  # depósito + pedidos
    # Distancias/duración triviales: todo a 0 metros (no afecta la factibilidad).
    fake_dist = [[0] * n for _ in range(n)]
    fake_dur = [[600] * n for _ in range(n)]  # 10 min entre todo
    with patch(
        "app.services.optimizer.get_distance_duration_matrix",
        return_value=(fake_dist, fake_dur),
    ):
        result = optimize_routes(orders, vehicles)
    assert result["success"] is True
    assert result["matrix_source"] == "ors"
