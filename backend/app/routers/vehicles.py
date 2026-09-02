from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vehicle import Vehicle
from app.models.user import User, RoleEnum
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleOut
from app.auth.dependencies import get_current_user, require_role

router = APIRouter(prefix="/api/vehicles", tags=["Vehículos"])


def _validate_driver(db: Session, driver_id: int | None) -> None:
    """Verifica que driver_id exista y tenga rol conductor (si se envía)."""
    if driver_id is None:
        return
    driver = db.query(User).filter(User.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=400, detail="El conductor asignado no existe")
    if driver.role != RoleEnum.conductor:
        raise HTTPException(
            status_code=400,
            detail="El conductor asignado debe tener rol 'conductor'",
        )


@router.get("/", response_model=List[VehicleOut])
@router.get("", response_model=List[VehicleOut], include_in_schema=False)
def list_vehicles(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Vehicle).all()


@router.post("/", response_model=VehicleOut)
def create_vehicle(
    vehicle_in: VehicleCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin, RoleEnum.planificador])),
):
    _validate_driver(db, vehicle_in.driver_id)
    vehicle = Vehicle(**vehicle_in.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/{vehicle_id}", response_model=VehicleOut)
def get_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return vehicle


@router.put("/{vehicle_id}", response_model=VehicleOut)
def update_vehicle(
    vehicle_id: int,
    vehicle_in: VehicleUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin, RoleEnum.planificador])),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    _validate_driver(db, vehicle_in.driver_id)
    for field, value in vehicle_in.model_dump(exclude_unset=True).items():
        setattr(vehicle, field, value)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.delete("/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Eliminar vehículo (solo admin). Rechaza si tiene rutas asociadas."""
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    from app.models.route import Route

    if db.query(Route).filter(Route.vehicle_id == vehicle_id).first():
        raise HTTPException(
            status_code=400, detail="No se puede eliminar: tiene rutas asociadas"
        )
    db.delete(vehicle)
    db.commit()
    return {"detail": "Vehículo eliminado"}
