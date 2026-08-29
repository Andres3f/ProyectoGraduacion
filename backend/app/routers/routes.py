from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.order import Order, OrderStatus
from app.models.vehicle import Vehicle
from app.models.user import User, RoleEnum
from app.schemas.route import (
    RouteOut, OptimizeRequest, OptimizeResponse,
)
from app.auth.dependencies import get_current_user, require_role
from app.services.optimizer import optimize_routes
from app.services.metrics import compare_before_after

router = APIRouter(prefix="/api/routes", tags=["Rutas"])


@router.get("/", response_model=List[RouteOut])
def list_routes(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Route).all()


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

        for stop in route_data["stops"]:
            stop_row = RouteStop(
                route_id=route.id,
                order_id=stop["order_id"],
                sequence=stop["sequence"],
                eta=stop["eta"],
                distance_from_previous_km=stop["distance_from_previous_km"],
            )
            db.add(stop_row)
            assigned_order_ids.add(stop["order_id"])

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
    _: User = Depends(get_current_user),
):
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    return route
