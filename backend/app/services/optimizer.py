"""
Servicio de optimización de rutas con OR-Tools (CVRP).
Capacitated Vehicle Routing Problem para rutas de cemento en Jalapa.
"""

import math
from typing import List

from ortools.constraint_solver import routing_enums_pb2, pywrapcp


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia Haversine en km entre dos coordenadas."""
    R = 6371  # Radio de la Tierra en km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _build_distance_matrix(locations: List[dict]) -> List[List[int]]:
    """Construye una matriz de distancias (en metros) entre ubicaciones."""
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = _haversine(
                    locations[i]["lat"], locations[i]["lng"],
                    locations[j]["lat"], locations[j]["lng"],
                )
                matrix[i][j] = int(dist * 1000)  # metros
    return matrix


def optimize_route(orders) -> dict:
    """
    Optimiza el orden de visita usando OR-Tools TSP solver.
    Recibe una lista de objetos Order (SQLAlchemy).
    Retorna un diccionario con las paradas ordenadas y métricas.
    """
    # Depósito ficticio = primera orden como punto de partida
    depot = {"lat": orders[0].latitude, "lng": orders[0].longitude}
    locations = [depot] + [
        {"lat": o.latitude, "lng": o.longitude} for o in orders
    ]

    distance_matrix = _build_distance_matrix(locations)

    manager = pywrapcp.RoutingIndexManager(len(locations), 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        # Fallback: devolver orden original
        return {
            "stops": [
                {
                    "order_id": o.id,
                    "client_name": o.client_name,
                    "lat": o.latitude,
                    "lng": o.longitude,
                    "sequence": idx,
                }
                for idx, o in enumerate(orders)
            ],
            "total_distance_km": 0,
            "total_weight_kg": sum(o.weight_kg for o in orders),
        }

    # Extraer solución
    route_order = []
    index = routing.Start(0)
    total_distance = 0
    while not routing.IsEnd(index):
        node = manager.IndexToNode(index)
        next_index = solution.Value(routing.NextVar(index))
        total_distance += distance_matrix[node][manager.IndexToNode(next_index)]
        if node > 0:  # Ignorar depósito
            route_order.append(node - 1)  # Índice del pedido
        index = next_index

    stops = [
        {
            "order_id": orders[i].id,
            "client_name": orders[i].client_name,
            "lat": orders[i].latitude,
            "lng": orders[i].longitude,
            "sequence": seq,
        }
        for seq, i in enumerate(route_order)
    ]

    return {
        "stops": stops,
        "total_distance_km": round(total_distance / 1000, 2),
        "total_weight_kg": sum(orders[i].weight_kg for i in route_order),
    }
