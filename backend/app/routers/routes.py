import logging
from typing import List
from datetime import datetime, date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.order import Order, OrderStatus
from app.models.vehicle import Vehicle
from app.models.depot import Depot
from app.models.user import User, RoleEnum
from app.schemas.route import (
    RouteOut, OptimizeRequest, OptimizeResponse, AssignDriverRequest,
)
from app.auth.dependencies import get_current_user, require_role
from app.services.optimizer import optimize_routes
from app.services.metrics import compare_before_after
from app.services.ors_client import ORSError, get_route_geometry

router = APIRouter(prefix="/api/routes", tags=["Rutas"])

logger = logging.getLogger(__name__)


# Listado administrativo de todas las rutas; roles con gestión de rutas.
@router.get("/", response_model=List[RouteOut])
@router.get("", response_model=List[RouteOut], include_in_schema=False)
def list_routes(
    db: Session = Depends(get_db),
    _: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador, RoleEnum.gerente])
    ),
):
    """Listar todas las rutas (administrativo).

    Un conductor nunca debe ver las rutas de todos: usa `GET /api/routes/my-route`.
    """
    return db.query(Route).all()


# Consulta exclusiva del conductor: devuelve SU ruta en curso (o, si no
# existe, la planificada más reciente). Si ya terminó todas sus rutas, devuelve
# la última que completó para que vea el resumen de su trabajo.
@router.get("/my-route", response_model=RouteOut)
def get_my_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.conductor])),
):
    """Devuelve la ruta activa/pendiente del conductor autenticado (OPT-18)."""
    # Prioridad 1: ruta en curso.
    route = (
        db.query(Route)
        .filter(
            Route.driver_id == current_user.id,
            Route.status == RouteStatus.en_progreso,
        )
        .first()
    )
    # Prioridad 2: ruta planificada más reciente como siguiente trabajo.
    if not route:
        route = (
            db.query(Route)
            .filter(
                Route.driver_id == current_user.id,
                Route.status == RouteStatus.planificada,
            )
            .order_by(Route.created_at.desc())
            .first()
        )
    # Prioridad 3: la última ruta que ya terminó, como histórico inmediato.
    if not route:
        route = (
            db.query(Route)
            .filter(
                Route.driver_id == current_user.id,
                Route.status == RouteStatus.completada,
            )
            .order_by(Route.updated_at.desc())
            .first()
        )
    if not route:
        raise HTTPException(status_code=404, detail="No tienes rutas asignadas")
    return route


# Verifica que existan todos los pedidos solicitados antes de optimizar.
def _load_orders(db: Session, order_ids: List[int]) -> List[Order]:
    orders = db.query(Order).filter(Order.id.in_(order_ids)).all()
    if len(orders) != len(set(order_ids)):
        raise HTTPException(status_code=400, detail="Algunos pedidos no existen")
    return orders


# Verifica que existan los vehículos y que ninguno esté inactivo.
def _load_vehicles(db: Session, vehicle_ids: List[int]) -> List[Vehicle]:
    vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
    if len(vehicles) != len(set(vehicle_ids)):
        raise HTTPException(status_code=400, detail="Algunos vehículos no existen")
    # Los vehículos dados de baja no pueden participar en la optimización.
    inactive = [v.id for v in vehicles if not v.is_active]
    if inactive:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes vehículos no están activos: {inactive}",
        )
    return vehicles


# Resuelve el depósito principal de una ruta: el que tenga asignado y, si no
# tiene (rutas antiguas), el predeterminado de la BD. Como último recurso usa la
# coordenada de configuración, para no romper si la BD está vacía.
def _resolve_depot_coords(db: Session, depot_id) -> dict:
    depot = None
    if depot_id:
        depot = db.get(Depot, depot_id)
    if depot is None:
        depot = db.query(Depot).filter(Depot.is_default == True).first()
    if depot is None:
        return {"lat": settings.DEPOT_LAT, "lng": settings.DEPOT_LNG}
    return {"lat": depot.latitude, "lng": depot.longitude}


# Cálculo auxiliar de distancia geodésica (haversine) en línea recta.
def _straight_leg_km(coord_a: dict, coord_b: dict) -> float:
    """Distancia en línea recta (km) entre dos coordenadas."""
    import math

    d_lat = math.radians(coord_b["lat"] - coord_a["lat"])
    d_lng = math.radians(coord_b["lng"] - coord_a["lng"])
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(coord_a["lat"]))
        * math.cos(math.radians(coord_b["lat"]))
        * math.sin(d_lng / 2) ** 2
    )
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _apply_ors_duration_and_etas(
    stop_rows: List[RouteStop],
    coords: List[dict],
    duration_s: float,
) -> None:
    """Sobrescribe total_duration_min y recalcula el ETA de cada parada.

    Distribuye el tiempo real de ORS/OSRM proporcional a la distancia en línea
    recta de cada tramo (el backend no guarda la geometría tramo a tramo, así
    que esta es la aproximación más simple y determinista).

    ``coords`` es la secuencia del trayecto de **ida** (depósito al inicio y
    última parada al final) y ``duration_s`` su duración: los ETA son horas de
    llegada a las paradas, que todas ocurren antes de salir de nuevo del
    depósito. El regreso se contabiliza aparte en ``total_duration_min``.
    """
    rows = sorted(stop_rows, key=lambda r: r.sequence)
    # Proporción de cada tramo según su distancia en línea recta.
    leg_dists = [
        _straight_leg_km(coords[i], coords[i + 1])
        for i in range(len(coords) - 1)
    ]
    total_dist = sum(leg_dists)
    if total_dist <= 0:
        return

    # Hora de salida del depósito configurada en settings como base de los ETAs.
    base = datetime.combine(
        date.today(),
        datetime.strptime(settings.DEPOT_DEPARTURE, "%H:%M").time(),
    )
    # Distribuye la duración total proporcional a la distancia de cada tramo.
    cumul_min = 0.0
    for row, leg_dist in zip(rows, leg_dists):
        cumul_min += (duration_s / 60.0) * (leg_dist / total_dist)
        row.eta = base + timedelta(minutes=cumul_min)


def _tag_steps(steps: List[dict], leg: str) -> List[dict]:
    """Marca cada instrucción de manejo con el trayecto al que pertenece
    ("ida" o "vuelta") para que el panel del conductor las pueda separar."""
    return [{**s, "leg": leg} for s in steps]


# NOTA (OPT-11): se mantiene el endpoint `/api/routes/optimize` (recomendado
# por ser más RESTful que `/api/optimize`). Decisión documentada en PG-11.
@router.post("/optimize", response_model=OptimizeResponse)
def create_optimized_route(
    req: OptimizeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Crea y optimiza una o varias rutas a partir de pedidos y vehículos.

    Reasigna los pedidos entre los vehículos disponibles respetando capacidad
    en kg y ventanas de tiempo. Crea una fila Route por cada vehículo usado y
    sus RouteStop asociadas. Los pedidos pasan a estado ``en_ruta``.
    """
    # Valida pedidos y vehículos antes de llamar al optimizador.
    orders = _load_orders(db, req.order_ids)
    vehicles = _load_vehicles(db, req.vehicle_ids)

    result = optimize_routes(orders, vehicles, db)

    # Si no hubo asignación posible, se responde con los pedidos sin asignar.
    if not result["success"]:
        return OptimizeResponse(
            success=False,
            message=result["message"],
            unassigned_order_ids=list(result["unassigned_order_ids"]),
        )

    # El prefijo numérico de nombres se deriva de las rutas ya existentes.
    route_number_base = len(db.query(Route).all())
    created_routes = []
    assigned_order_ids = set()

    def _json_safe_stops(stops: list) -> list:
        """Convierte las paradas a un snapshot JSON serializable
        (eta datetime -> isoformat) para la columna de compatibilidad."""
        out = []
        for s in stops:
            item = dict(s)
            item["eta"] = s["eta"].isoformat() if s.get("eta") else None
            out.append(item)
        return out

    # Materializa cada ruta optimizada junto con sus paradas y el conductor
    # fijo del vehículo como responsable por defecto.
    for idx, route_data in enumerate(result["routes"]):
        vehicle = next(v for v in vehicles if v.id == route_data["vehicle_id"])
        route = Route(
            name=f"Ruta-{route_number_base + idx + 1}",
            vehicle_id=route_data["vehicle_id"],
            driver_id=vehicle.driver_id,
            depot_id=route_data.get("depot_id"),
            stops_snapshot=_json_safe_stops(route_data["stops"]),
            total_distance_km=route_data["total_distance_km"],
            total_weight_kg=route_data["total_weight_kg"],
            distance_source=result.get("matrix_source", "haversine"),
            status=RouteStatus.planificada,
            optimized_at=None,
        )
        db.add(route)
        db.flush()  # obtener route.id

        created_stop_rows = []
        for stop in route_data["stops"]:
            stop_row = RouteStop(
                route_id=route.id,
                order_id=stop["order_id"],
                sequence=stop["sequence"],
                eta=stop["eta"],
                distance_from_previous_km=stop["distance_from_previous_km"],
            )
            db.add(stop_row)
            created_stop_rows.append(stop_row)
            assigned_order_ids.add(stop["order_id"])

        # Geometría real por calle (ORS): si falla, la ruta se crea igual y el
        # mapa dibuja línea recta como respaldo. Nunca rompemos la creación.
        # Se piden los dos tramos por separado (ida y vuelta) para que el mapa
        # pueda dibujarlos con colores distintos.
        try:
            depot_coords = _resolve_depot_coords(db, route_data.get("depot_id"))
            stop_coords = [
                {"lat": s["lat"], "lng": s["lng"]} for s in route_data["stops"]
            ]
            # Ida: depósito -> paradas. Vuelta: última parada -> depósito.
            coords_out = [depot_coords] + stop_coords
            coords_back = stop_coords + [depot_coords]
            geo_out = get_route_geometry(coords_out)
            geo_back = get_route_geometry(coords_back)

            route.route_geometry = geo_out["geometry"]
            route.route_geometry_return = geo_back["geometry"]
            # Las instrucciones de ambos tramos, etiquetadas por trayecto.
            route.steps = _tag_steps(geo_out["steps"], "ida") + _tag_steps(
                geo_back["steps"], "vuelta"
            )
            # La duración total de la ruta es la ida y vuelta completas.
            route.total_duration_min = round(
                (geo_out["duration_s"] + geo_back["duration_s"]) / 60, 1
            )
            # Los ETA se reparten solo sobre el trayecto de ida.
            _apply_ors_duration_and_etas(
                created_stop_rows, coords_out, geo_out["duration_s"]
            )
        except ORSError as exc:
            logger.warning(
                "No se pudo obtener geometría real de ORS (%s). Línea recta.", exc
            )
            route.route_geometry = None
            route.route_geometry_return = None
            route.steps = None

        created_routes.append(route)

    # Los pedidos asignados pasan al estado "en_ruta" (OPT-13).
    db.query(Order).filter(Order.id.in_(assigned_order_ids)).update(
        {Order.status: OrderStatus.en_ruta}, synchronize_session=False
    )

    from app.services.audit import log_action

    # Registra la optimización en el log de auditoría con su resumen.
    log_action(
        db, current_user.id, "optimizar_rutas",
        entidad="route", detalle={
            "routes_creadas": len(created_routes),
            "unassigned": len(result["unassigned_order_ids"]),
            "matrix_source": result.get("matrix_source", "haversine"),
        },
    )
    db.commit()
    for route in created_routes:
        db.refresh(route)

    # Calcula el ahorro comparando la ruta naive contra la optimizada.
    metrics = compare_before_after(
        orders,
        [r["stops"] for r in result["routes"]],
    )

    return OptimizeResponse(
        success=True,
        routes=created_routes,
        unassigned_order_ids=list(result["unassigned_order_ids"]),
        metrics=metrics,
        matrix_source=result.get("matrix_source", "haversine"),
    )


# Cierre de ruta: el conductor confirma que ya volvió al depósito. Hasta que no
# lo haga la ruta sigue `en_progreso` y el mapa permanece visible, porque el
# trayecto de regreso todavía no ha terminado.
@router.put("/{route_id}/complete", response_model=RouteOut)
def complete_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.conductor])),
):
    """Marca la ruta del conductor como completada al regresar al depósito.

    Solo el conductor asignado puede cerrarla, y solo cuando todas sus paradas
    ya están resueltas: si faltara alguna, el regreso no se puede confirmar.
    """
    route = (
        db.query(Route)
        .filter(Route.id == route_id, Route.driver_id == current_user.id)
        .first()
    )
    # 404 (y no 403) para no confirmar la existencia de rutas ajenas.
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    # Idempotente: cerrar una ruta ya cerrada no es un error.
    if route.status == RouteStatus.completada:
        return route

    pending = [
        s for s in route.stops if s.status not in ("entregado", "fallido")
    ]
    if pending:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Aún tienes {len(pending)} parada(s) sin resolver. "
                "Resuélvelas antes de confirmar el regreso al depósito."
            ),
        )

    route.status = RouteStatus.completada
    db.add(route)

    from app.services.audit import log_action

    log_action(
        db, current_user.id, "completar_ruta",
        entidad="route", entidad_id=route_id,
    )
    db.commit()
    db.refresh(route)
    return route


# Detalle de ruta: cualquier autenticado, pero los conductores solo la propia.
@router.get("/{route_id}", response_model=RouteOut)
def get_route(
    route_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    # PG-18: un conductor solo puede ver sus propias rutas. Se devuelve 404
    # (y no 403) para no confirmar la existencia de rutas ajenas.
    if current_user.role == RoleEnum.conductor and route.driver_id != current_user.id:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return route


# Cambio de conductor sobre una ruta ya generada (admin y planificador).
@router.put("/{route_id}/assign-driver", response_model=RouteOut)
def assign_driver(
    route_id: int,
    body: AssignDriverRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.planificador, RoleEnum.admin])),
):
    """Asigna/reasigna el conductor de una ruta ya generada.

    La optimización asigna por defecto el conductor "fijo" del vehículo
    (vehicle.driver_id); este endpoint permite que el planificador lo cambie
    después, por ejemplo cuando el conductor titular no puede servir ese día.
    """
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")

    # El nuevo conductor debe ser un usuario con rol conductor y estar activo.
    driver = db.query(User).filter(
        User.id == body.driver_id,
        User.role == RoleEnum.conductor,
        User.is_active == True,
    ).first()
    if not driver:
        raise HTTPException(
            status_code=400,
            detail="El usuario indicado no es un conductor activo",
        )

    route.driver_id = body.driver_id
    db.add(route)
    db.commit()
    db.refresh(route)
    return route
