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


@router.get("/my-route", response_model=RouteOut)
def get_my_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.conductor])),
):
    """Devuelve la ruta activa/pendiente del conductor autenticado (OPT-18)."""
    route = (
        db.query(Route)
        .filter(
            Route.driver_id == current_user.id,
            Route.status == RouteStatus.en_progreso,
        )
        .first()
    )
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
    if not route:
        raise HTTPException(status_code=404, detail="No tienes rutas asignadas")
    return route


def _load_orders(db: Session, order_ids: List[int]) -> List[Order]:
    orders = db.query(Order).filter(Order.id.in_(order_ids)).all()
    if len(orders) != len(set(order_ids)):
        raise HTTPException(status_code=400, detail="Algunos pedidos no existen")
    return orders


def _load_vehicles(db: Session, vehicle_ids: List[int]) -> List[Vehicle]:
    vehicles = db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all()
    if len(vehicles) != len(set(vehicle_ids)):
        raise HTTPException(status_code=400, detail="Algunos vehículos no existen")
    inactive = [v.id for v in vehicles if not v.is_active]
    if inactive:
        raise HTTPException(
            status_code=400,
            detail=f"Los siguientes vehículos no están activos: {inactive}",
        )
    return vehicles


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

    Distribuye el tiempo real de ORS proporcional a la distancia en línea
    recta de cada tramo (el backend no guarda la geometría tramo a tramo, así
    que esta es la aproximación más simple y determinista).
    """
    rows = sorted(stop_rows, key=lambda r: r.sequence)
    leg_dists = [
        _straight_leg_km(coords[i], coords[i + 1])
        for i in range(len(coords) - 1)
    ]
    total_dist = sum(leg_dists)
    if total_dist <= 0:
        return

    base = datetime.combine(
        date.today(),
        datetime.strptime(settings.DEPOT_DEPARTURE, "%H:%M").time(),
    )
    cumul_min = 0.0
    for row, leg_dist in zip(rows, leg_dists):
        cumul_min += (duration_s / 60.0) * (leg_dist / total_dist)
        row.eta = base + timedelta(minutes=cumul_min)


# NOTA (OPT-11): se mantiene el endpoint `/api/routes/optimize` (recomendado
# por ser más RESTful que `/api/optimize`). Decisión documentada en PG-11.
@router.post("/optimize", response_model=OptimizeResponse)
def create_optimized_route(
    req: OptimizeRequest,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Crea y optimiza una o varias rutas a partir de pedidos y vehículos.

    Reasigna los pedidos entre los vehículos disponibles respetando capacidad
    en kg y ventanas de tiempo. Crea una fila Route por cada vehículo usado y
    sus RouteStop asociadas. Los pedidos pasan a estado ``en_ruta``.
    """
    orders = _load_orders(db, req.order_ids)
    vehicles = _load_vehicles(db, req.vehicle_ids)

    result = optimize_routes(orders, vehicles)

    if not result["success"]:
        return OptimizeResponse(
            success=False,
            message=result["message"],
            unassigned_order_ids=list(result["unassigned_order_ids"]),
        )

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

    for idx, route_data in enumerate(result["routes"]):
        vehicle = next(v for v in vehicles if v.id == route_data["vehicle_id"])
        route = Route(
            name=f"Ruta-{route_number_base + idx + 1}",
            vehicle_id=route_data["vehicle_id"],
            driver_id=vehicle.driver_id,
            stops_snapshot=_json_safe_stops(route_data["stops"]),
            total_distance_km=route_data["total_distance_km"],
            total_weight_kg=route_data["total_weight_kg"],
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
        try:
            coords = [{"lat": settings.DEPOT_LAT, "lng": settings.DEPOT_LNG}] + [
                {"lat": s["lat"], "lng": s["lng"]} for s in route_data["stops"]
            ]
            geo = get_route_geometry(coords)
            route.route_geometry = geo["geometry"]
            route.steps = geo["steps"]
            route.total_duration_min = round(geo["duration_s"] / 60, 1)
            _apply_ors_duration_and_etas(
                created_stop_rows, coords, geo["duration_s"]
            )
        except ORSError as exc:
            logger.warning(
                "No se pudo obtener geometría real de ORS (%s). Línea recta.", exc
            )
            route.route_geometry = None
            route.steps = None

        created_routes.append(route)

    # Los pedidos asignados pasan al estado "en_ruta" (OPT-13).
    db.query(Order).filter(Order.id.in_(assigned_order_ids)).update(
        {Order.status: OrderStatus.en_ruta}, synchronize_session=False
    )

    db.commit()
    for route in created_routes:
        db.refresh(route)

    metrics = compare_before_after(
        orders,
        [r["stops"] for r in result["routes"]],
    )

    return OptimizeResponse(
        success=True,
        routes=created_routes,
        unassigned_order_ids=list(result["unassigned_order_ids"]),
        metrics=metrics,
    )


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
