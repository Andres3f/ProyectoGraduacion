"""
Métricas "antes vs después" de una optimización de rutas.

Compara la distancia de la ruta en el orden original (como llegaron los
pedidos, sin optimizar) contra la distancia de la ruta optimizada, y estima
el ahorro de combustible usando un costo por kilómetro configurable.
"""

from typing import List

from app.config import settings
from app.services.optimizer import _haversine


def _default_depot_point() -> dict:
    # Coordenada base de comparación (settings), usada como origen/retorno de
    # la ruta "naive". El optimizador ya resuelve el depósito real por ruta.
    return {"lat": settings.DEPOT_LAT, "lng": settings.DEPOT_LNG}


def _point(stop) -> dict:
    """Normaliza un punto (objeto Order o dict) a {lat, lng}."""
    # Acepta tanto objetos SQLAlchemy como dicts con claves lat/latitude y lng/longitude.
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
    depot = _default_depot_point()
    total = 0.0
    prev = depot
    # Suma la distancia entre paradas consecutivas partiendo del depósito.
    for stop in stops:
        p = _point(stop)
        total += _haversine(prev["lat"], prev["lng"], p["lat"], p["lng"])
        prev = p
    # Cierra el recorrido de vuelta al depósito y aplica el factor de calles.
    total += _haversine(prev["lat"], prev["lng"], depot["lat"], depot["lng"])
    return total * settings.ROAD_DISTANCE_FACTOR


def estimate_savings(distance_saved_km: float, time_saved_min: float = 0) -> dict:
    """Estima el ahorro de combustible y de costo operativo (PG-22).

    Args:
        distance_saved_km: kilómetros evitados por la optimización.
        time_saved_min: minutos de tiempo de conductor ahorrados.

    Returns:
        dict con fuel_liters_saved, fuel_cost_saved_gtq y
        operational_cost_saved_gtq (combustible + mano de obra).
    """
    if distance_saved_km <= 0:
        return {
            "fuel_liters_saved": 0.0,
            "fuel_cost_saved_gtq": 0.0,
            "operational_cost_saved_gtq": 0.0,
        }
    # Litros = km evitados / rendimiento por litro; costo = litros * precio.
    liters_saved = distance_saved_km / settings.FUEL_CONSUMPTION_KM_PER_LITER
    fuel_cost_saved = liters_saved * settings.FUEL_PRICE_GTQ_PER_LITER
    # Mano de obra ahorrada: minutos convertidos a horas por el costo de conductor.
    driver_cost_saved = (time_saved_min / 60) * settings.DRIVER_COST_GTQ_PER_HOUR
    return {
        "fuel_liters_saved": round(liters_saved, 1),
        "fuel_cost_saved_gtq": round(fuel_cost_saved, 2),
        "operational_cost_saved_gtq": round(fuel_cost_saved + driver_cost_saved, 2),
    }


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
    # Si llegan varias listas (una por vehículo), se suman los subtotales.
    if optimized_stops and isinstance(optimized_stops[0], list):
        optimized_distance = sum(
            _total_distance_in_order(route) for route in optimized_stops
        )
    else:
        optimized_distance = _total_distance_in_order(optimized_stops)

    # Diferencia de la línea base al escenario optimizado y su porcentaje.
    fuel_savings_distance = naive_distance - optimized_distance
    reduction_pct = (
        round((1 - optimized_distance / naive_distance) * 100, 1)
        if naive_distance else 0
    )
    # Ahorro monetario estimado: km evitados × costo por kilómetro.
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
