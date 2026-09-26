from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.depot import Depot
from app.models.vehicle import Vehicle
from app.models.user import User, RoleEnum
from app.schemas.depot import DepotCreate, DepotUpdate, DepotOut
from app.auth.dependencies import get_current_user, require_role
from app.services.geo import point_wkt

router = APIRouter(prefix="/api/depots", tags=["Depósitos"])


# Cualquier usuario autenticado puede consultar los depósitos (para dibujarlos
# en el mapa de rutas). Se declara con y sin slash final por robustez.
@router.get("/", response_model=List[DepotOut])
@router.get("", response_model=List[DepotOut], include_in_schema=False)
def list_depots(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return db.query(Depot).order_by(Depot.name).all()


# Alta de depósito: solo admin. Si se marca is_default, desmarca los demás
# para garantizar que siempre exista exactamente un depósito predeterminado.
@router.post("/", response_model=DepotOut, status_code=status.HTTP_201_CREATED)
def create_depot(
    depot_in: DepotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    data = depot_in.model_dump()
    if data["is_default"]:
        db.query(Depot).update({"is_default": False})
    depot = Depot(
        **data,
        geom=point_wkt(data["longitude"], data["latitude"]),
    )
    db.add(depot)
    from app.services.audit import log_action
    log_action(db, current_user.id, "crear_deposito", entidad="depot")
    db.commit()
    db.refresh(depot)
    return depot


@router.put("/{depot_id}", response_model=DepotOut)
def update_depot(
    depot_id: int,
    depot_in: DepotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    """Actualizar depósito. Recalcula la geometría si cambian coordenadas."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    data = depot_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(depot, field, value)
    depot.geom = point_wkt(
        getattr(depot, "longitude"),
        getattr(depot, "latitude"),
    )
    from app.services.audit import log_action
    log_action(
        db, current_user.id, "actualizar_deposito", entidad="depot",
        entidad_id=depot_id,
    )
    db.commit()
    db.refresh(depot)
    return depot


# Cambia el depósito predeterminado: desmarca cualquier otro antes de marcar
# este, garantizando la regla de "exactamente un default".
@router.put("/{depot_id}/set-default", response_model=DepotOut)
def set_default_depot(
    depot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    db.query(Depot).update({"is_default": False})
    depot.is_default = True
    from app.services.audit import log_action
    log_action(
        db, current_user.id, "cambiar_deposito_predeterminado",
        entidad="depot", entidad_id=depot_id,
    )
    db.commit()
    db.refresh(depot)
    return depot


@router.delete("/{depot_id}")
def delete_depot(
    depot_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    """Eliminar depósito (solo admin). Protege el default y los vehículos."""
    depot = db.query(Depot).filter(Depot.id == depot_id).first()
    if not depot:
        raise HTTPException(status_code=404, detail="Depósito no encontrado")
    if depot.is_default:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede eliminar el depósito predeterminado. "
                "Marca otro como predeterminado primero."
            ),
        )
    if db.query(Vehicle).filter(Vehicle.depot_id == depot_id).first():
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: hay vehículos asignados a este depósito",
        )
    from app.services.audit import log_action
    log_action(
        db, current_user.id, "eliminar_deposito", entidad="depot",
        entidad_id=depot_id,
    )
    db.delete(depot)
    db.commit()
    return {"detail": "Depósito eliminado"}