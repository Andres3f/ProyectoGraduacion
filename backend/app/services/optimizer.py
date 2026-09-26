"""
Servicio de optimización de rutas con OR-Tools (CVRP + ventanas de tiempo).

Resuelve un Vehicle Routing Problem con capacidad (CVRP) y ventanas de
tiempo para las rutas de cemento en Jalapa. A diferencia de la versión
anterior (TSP de un solo vehículo), aquí cada vehículo disponible puede
recibir una ruta y se respetan la capacidad en kg y los horarios de entrega.

Decisión de diseño (documentada en el README): se usa distancia Haversine
(línea recta) multiplicada por un factor de corrección de caminos (por
defecto 1.3) en lugar de levantar un servidor OSRM. Para el alcance de una
tesis esto es suficiente y mucho más simple de desplegar.
"""

import math
import logging
from datetime import datetime, date, timedelta
from types import SimpleNamespace
from typing import List, Optional

from ortools.constraint_solver import routing_enums_pb2, pywrapcp

from app.config import settings
from app.services.ors_client import get_distance_duration_matrix, ORSError

logger = logging.getLogger(__name__)


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
    """Matriz de distancias en metros (con factor de corrección de calles)."""
    factor = settings.ROAD_DISTANCE_FACTOR
    n = len(locations)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                dist = _haversine(
                    locations[i]["lat"], locations[i]["lng"],
                    locations[j]["lat"], locations[j]["lng"],
                )
                matrix[i][j] = int(dist * 1000 * factor)  # metros
    return matrix


def _build_time_matrix(distance_matrix: List[List[int]]) -> List[List[int]]:
    """Matriz de tiempos de viaje (minutos) a partir de la distancia y la
    velocidad promedio configurable."""
    speed_kmh = settings.AVERAGE_SPEED_KMH if settings.AVERAGE_SPEED_KMH > 0 else 30.0
    n = len(distance_matrix)
    matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                # minutos = metros / 1000 / (km/h) * 60
                minutes = (distance_matrix[i][j] / 1000.0) / speed_kmh * 60
                # Mínimo 1 minuto para que el solver no asuma viajes sin costo.
                matrix[i][j] = max(1, int(round(minutes)))
    return matrix


def _service_time_minutes(order) -> int:
    # Tiempo de descarga en cada parada (minutos) o 0 si no está definido.
    return int(order.service_time_min) if order.service_time_min else 0


def _estimate_arrival_datetime(cumul_minutes: float) -> datetime:
    """Convierte una cantidad de minutos desde la salida del depósito en un
    datetime estimado, tomando como base la hora de salida configurada."""
    base = datetime.combine(date.today(), datetime.strptime(
        settings.DEPOT_DEPARTURE, "%H:%M"
    ).time())
    return base + timedelta(minutes=int(cumul_minutes))


def optimize_routes(orders: list, vehicles: list, db=None) -> dict:
    """Optimiza la asignación de pedidos a varios vehículos (VRP con
    capacidad y ventanas de tiempo).

    Todos los vehículos salen y regresan del **depósito principal** (el de la
    BD con ``is_default=True``), que es el único punto de partida del sistema.
    Por eso el modelo usa un solo nodo de depósito como inicio y fin de todas
    las rutas, sin importar el ``depot_id`` que tenga cada vehículo.

    Args:
        orders: lista de objetos Order (SQLAlchemy).
        vehicles: lista de objetos Vehicle disponibles (is_active).
        db: Session SQLAlchemy para leer el depósito principal. Si es ``None``
            (tests unitarios / compatibilidad) se usa la coordenada de
            ``settings.DEPOT_LAT``/``DEPOT_LNG`` como depósito principal.

    Returns:
        dict con:
          - success: bool
          - message: Optional[str]
          - routes: list[dict], una por vehículo usado (incluye depot_id)
          - unassigned_order_ids: list[int] ordenes que no pudieron asignarse
    """
    num_vehicles = len(vehicles)
    if num_vehicles == 0:
        return {
            "success": False,
            "message": "No hay vehículos disponibles para optimizar.",
            "routes": [],
            "unassigned_order_ids": [o.id for o in orders],
        }
    if not orders:
        return {
            "success": True,
            "message": "No hay pedidos para optimizar.",
            "routes": [],
            "unassigned_order_ids": [],
        }

    # ── Depósito principal de salida ──────────────────────────
    # Se lee el depósito predeterminado desde la BD; si no hay (o no se pasó
    # db), se degrada a la coordenada de configuración (compatibilidad).
    main_depot = None
    if db is not None:
        from app.models.depot import Depot
        main_depot = db.query(Depot).filter(Depot.is_default == True).first()
        if not main_depot:
            return {
                "success": False,
                "message": "No hay un depósito predeterminado configurado.",
                "routes": [],
                "unassigned_order_ids": [o.id for o in orders],
                "matrix_source": None,
            }
    if main_depot is None:
        main_depot = SimpleNamespace(
            id=None, latitude=settings.DEPOT_LAT, longitude=settings.DEPOT_LNG,
        )

    # El depósito principal es el nodo 0: inicio y fin de todas las rutas.
    num_depots = 1
    depot_locations = [{"lat": main_depot.latitude, "lng": main_depot.longitude}]
    order_locations = [{"lat": o.latitude, "lng": o.longitude} for o in orders]
    locations = depot_locations + order_locations

    starts = [0] * num_vehicles
    ends = starts  # todos los vehículos regresan al depósito principal

    # ── Matriz de distancias/tiempos ────────────────────────────
    # Se intenta OpenRouteService (distancias reales por carretera); si falla
    # o no hay API key, se usa Haversine como fallback exactamente como antes.
    try:
        distance_matrix, duration_matrix_sec = get_distance_duration_matrix(locations)
        # Convierte duraciones de segundos a minutos enteros (mínimo 1).
        time_matrix = [[max(1, round(d / 60)) for d in row] for row in duration_matrix_sec]
        matrix_source = "ors"
    except ORSError as e:
        logger.warning("ORS no disponible (%s), usando Haversine como fallback.", e)
        distance_matrix = _build_distance_matrix(locations)
        time_matrix = _build_time_matrix(distance_matrix)
        matrix_source = "haversine"

    # Capacidad en kg de cada vehículo y demanda (peso) de cada pedido.
    # La demanda de cada depósito se fija en 0.
    vehicle_capacities = [
        int(v.capacity_kg) if v.capacity_kg else 0 for v in vehicles
    ]
    demands = [0] * num_depots + [int(o.weight_kg) for o in orders]

    # Crea el índice y el modelo de enrutado: todas las rutas arrancan y
    # terminan en el nodo 0 (depósito principal).
    manager = pywrapcp.RoutingIndexManager(
        len(locations), num_vehicles, starts, ends
    )
    routing = pywrapcp.RoutingModel(manager)

    # ── Costo: distancia (metros) ──────────────────────────────
    # Función de costo por arco: minimizar los metros recorridos por cada vehículo.
    def distance_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return distance_matrix[from_node][to_node]

    distance_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(distance_callback_index)

    # ── Dimensión de capacidad (CVRP) ──────────────────────────
    # Suma la demanda (kg) acumulada por vehículo sin exceder su capacidad.
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return demands[from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # sin holgura
        vehicle_capacities,
        True,  # start cumul to zero
        "Capacity",
    )

    # ── Dimensión de tiempo (viaje + servicio) ─────────────────
    # Acumula tiempo de viaje más tiempo de descarga en cada parada.
    service_times = [0] * num_depots + [_service_time_minutes(o) for o in orders]

    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        # El servicio se cuenta al llegar al nodo destino (los depósitos no atienden).
        service = service_times[to_node] if to_node >= num_depots else 0
        return time_matrix[from_node][to_node] + service

    time_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.AddDimension(
        time_callback_index,
        30,  # slack (minutos de espera permitidos)
        settings.MAX_TIME_PER_VEHICLE_MIN,  # tiempo máximo por vehículo
        False,  # no empieza en cero; lo fijamos con la ventana del depósito
        "Time",
    )
    time_dimension = routing.GetDimensionOrDie("Time")

    # Ventana del depósito principal: la hora de salida nominal (p. ej. 08:00)
    # solo se usa para mostrar los ETA; el solver puede salir dentro del día.
    depot_index = manager.NodeToIndex(0)
    time_dimension.CumulVar(depot_index).SetRange(0, settings.MAX_TIME_PER_VEHICLE_MIN)

    # Ventanas de tiempo de cada pedido (minutos del día). La interfaz las
    # captura como HH:MM (ej. 14:00 -> 840) y las guarda en minutos.
    for idx, order in enumerate(orders):
        node_index = manager.NodeToIndex(num_depots + idx)
        tw_start = order.time_window_start
        tw_end = order.time_window_end
        if tw_start is not None and tw_end is not None:
            time_dimension.CumulVar(node_index).SetRange(int(tw_start), int(tw_end))

    # Ventanas de tiempo de inicio/fin para cada vehículo (start/end span).
    for vehicle_idx in range(num_vehicles):
        time_dimension.CumulVar(routing.Start(vehicle_idx)).SetRange(
            0, settings.MAX_TIME_PER_VEHICLE_MIN
        )
        time_dimension.CumulVar(routing.End(vehicle_idx)).SetRange(
            0, settings.MAX_TIME_PER_VEHICLE_MIN
        )

    # ── Disyunciones: permitir dejar pedidos sin asignar ───────
    # Cada nodo puede "caerse" de la solución pagando una penalización
    # grande. Así, si un pedido excede capacidad, tiempo o ventana, no rompe
    # la ruta sino que se reporta como no asignado.
    big_number = int(sum(distance_matrix[i][j] for i in range(len(locations)) for j in range(len(locations)))) + 10000
    for node in range(num_depots, len(locations)):
        routing.AddDisjunction([manager.NodeToIndex(node)], big_number)

    # ── Estrategia de búsqueda ─────────────────────────────────
    # Heurística PATH_CHEAPEST_ARC + límite de 10 s para respuestas rápidas.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.time_limit.seconds = 10

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return {
            "success": False,
            "message": "No se encontró una asignación factible con la capacidad/ventanas dadas.",
            "routes": [],
            "unassigned_order_ids": [o.id for o in orders],
        }

    # ── Extraer rutas por vehículo ─────────────────────────────
    # Recorre la solución siguiendo los NextVar de cada vehículo.
    routes = []
    visited_node_indices = set()
    for vehicle_idx in range(num_vehicles):
        index = routing.Start(vehicle_idx)
        stops = []
        prev_node = manager.IndexToNode(routing.Start(vehicle_idx))  # depósito principal
        route_distance = 0
        route_weight = 0

        # Avanza por la cadena de nodos del vehículo hasta volver a su depósito.
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            visited_node_indices.add(node)
            next_index = solution.Value(routing.NextVar(index))
            next_node = manager.IndexToNode(next_index)

            if node >= num_depots:  # pedido real (el nodo 0 es el depósito)
                order = orders[node - num_depots]
                # ETA estimada = hora de salida + minutos acumulados del solver.
                arrival_min = solution.Value(time_dimension.CumulVar(index))
                # Distancia del tramo anterior a este nodo (metros).
                leg_distance_m = distance_matrix[prev_node][node]
                stops.append({
                    "order_id": order.id,
                    "client_name": order.client_name,
                    "lat": order.latitude,
                    "lng": order.longitude,
                    "sequence": len(stops),
                    "eta": _estimate_arrival_datetime(arrival_min),
                    "distance_from_previous_km": round(leg_distance_m / 1000.0, 2),
                })
                route_weight += order.weight_kg

            route_distance += distance_matrix[node][next_node]
            prev_node = node
            index = next_index

        # Solo se registra la ruta si el vehículo tiene al menos una parada.
        if stops:
            routes.append({
                "vehicle_id": vehicles[vehicle_idx].id,
                "depot_id": main_depot.id,
                "stops": stops,
                "total_distance_km": round(route_distance / 1000.0, 2),
                "total_weight_kg": round(route_weight, 2),
            })

    # ── Pedidos no asignados ───────────────────────────────────
    # Índice num_depots+i del nodo no visitado por ninguna ruta = pedido sin asignar.
    unassigned = [
        o.id for i, o in enumerate(orders)
        if (num_depots + i) not in visited_node_indices
    ]

    return {
        "success": True,
        "message": None,
        "routes": routes,
        "unassigned_order_ids": unassigned,
        "matrix_source": matrix_source,
    }
