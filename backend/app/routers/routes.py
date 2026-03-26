from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.route import Route
from app.models.order import Order
from app.models.user import User, RoleEnum
from app.schemas.route import RouteCreate, RouteOut
from app.auth.dependencies import get_current_user, require_role
from app.services.optimizer import optimize_route

router = APIRouter(prefix="/api/routes", tags=["Rutas"])


@router.get("/", response_model=List[RouteOut])
def list_routes(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Route).all()


@router.post("/optimize", response_model=RouteOut)
def create_optimized_route(
    route_in: RouteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Crea y optimiza una ruta a partir de IDs de pedidos."""
    orders = db.query(Order).filter(Order.id.in_(route_in.order_ids)).all()
    if len(orders) != len(route_in.order_ids):
        raise HTTPException(status_code=400, detail="Algunos pedidos no existen")

    result = optimize_route(orders)

    route = Route(
        name=route_in.name or f"Ruta-{len(db.query(Route).all()) + 1}",
        vehicle_id=route_in.vehicle_id,
        driver_id=route_in.driver_id,
        stops=result["stops"],
        total_distance_km=result["total_distance_km"],
        total_weight_kg=result["total_weight_kg"],
    )
    db.add(route)
    db.commit()
    db.refresh(route)
    return route


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
