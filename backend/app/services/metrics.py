"""
Métricas "antes vs después" de una optimización de rutas.

Compara la distancia de la ruta en el orden original (como llegaron los
pedidos, sin optimizar) contra la distancia de la ruta optimizada, y estima
el ahorro de combustible usando un costo por kilómetro configurable.
"""

from typing import List

from app.config import settings
from app.services.optimizer import _haversine, _depot


def _point(stop) -> dict:
    """Normaliza un punto (objeto Order o dict) a {lat, lng}."""
    if isinstance(stop, dict):
        lat = stop.get("lat", stop.get("latitude"))
        lng = stop.get("lng", stop.get("longitude"))
    else:
        lat = getattr(stop, "latitude", None)
        lng = getattr(stop, "longitude", None)
    return {"lat": float(lat), "lng": float(lng)}


def _total_distance_in_order(stops: List) -> float:
    """Distancia redonda en km: depósito -> paradas en orden -> depósito.

    Usa distancia Haversine con el mismo factor de corrección de calles que
    el optimizador, para comparar manzanas con manzanas.
    """
    depot = _depot()
    total = 0.0
    prev = depot
    for stop in stops:
        p = _point(stop)
        total += _haversine(prev["lat"], prev["lng"], p["lat"], p["lng"])
        prev = p
    total += _haversine(prev["lat"], prev["lng"], depot["lat"], depot["lng"])
    return total * settings.ROAD_DISTANCE_FACTOR


def compare_before_after(orders: List, optimized_stops) -> dict:
    """Calcula las métricas antes/después de la optimización.

    Args:
        orders: pedidos en su orden original (naive), objetos Order o dicts.
        optimized_stops: paradas ya ordenadas/optimizadas. Puede ser una sola
            lista (una ruta) o una lista de listas (una por vehículo).

    Returns:
        dict con distance_before_km, distance_after_km, reduction_percentage
        y estimated_fuel_savings_gtq.
    """
    naive_distance = _total_distance_in_order(orders)

    # "Después": suma de la distancia redonda de cada ruta optimizada.
    if optimized_stops and isinstance(optimized_stops[0], list):
        optimized_distance = sum(
            _total_distance_in_order(route) for route in optimized_stops
        )
    else:
        optimized_distance = _total_distance_in_order(optimized_stops)

    fuel_savings_distance = naive_distance - optimized_distance
    reduction_pct = (
        round((1 - optimized_distance / naive_distance) * 100, 1)
        if naive_distance else 0
    )
    fuel_savings = (
        round(fuel_savings_distance * settings.COST_PER_KM_GTQ, 2)
        if fuel_savings_distance > 0 else 0.0
    )

    return {
        "distance_before_km": round(naive_distance, 2),
        "distance_after_km": round(optimized_distance, 2),
        "reduction_percentage": reduction_pct,
        "estimated_fuel_savings_gtq": fuel_savings,
    }
