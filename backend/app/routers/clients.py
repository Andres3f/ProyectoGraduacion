from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.functions import ST_DWithin
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.client import Client
from app.models.order import Order
from app.models.user import User, RoleEnum
from app.schemas.client import ClientCreate, ClientUpdate, ClientOut
from app.auth.dependencies import get_current_user, require_role
from app.services.geo import point_wkt

router = APIRouter(prefix="/api/clients", tags=["Clientes"])


@router.get("/", response_model=List[ClientOut])
def list_clients(
    zone: Optional[str] = Query(None, description="Filtrar por zona"),
    name: Optional[str] = Query(None, description="Filtrar por nombre"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Listar clientes con filtros opcionales de zona y nombre."""
    query = db.query(Client)
    if zone:
        query = query.filter(Client.zone == zone)
    if name:
        query = query.filter(Client.name.ilike(f"%{name}%"))
    return query.all()


@router.get("/nearby", response_model=List[ClientOut])
def nearby_clients(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(5.0, gt=0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Clientes dentro de un radio (km) usando PostGIS ST_DWithin."""
    point = point_wkt(lng, lat)
    radius_m = radius_km * 1000
    query = db.query(Client).filter(
        ST_DWithin(Client.geom, point, radius_m)
    ).all()
    return query


@router.post("/", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    client_in: ClientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin, RoleEnum.planificador])),
):
    """Crear un nuevo cliente."""
    client = Client(
        **client_in.model_dump(),
        geom=point_wkt(client_in.longitude, client_in.latitude),
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.put("/{client_id}", response_model=ClientOut)
def update_client(
    client_id: int,
    client_in: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin, RoleEnum.planificador])),
):
    """Actualizar cliente. Recalcula la geometría si cambian coordenadas."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    data = client_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(client, field, value)
    client.geom = point_wkt(
        getattr(client, "longitude"),
        getattr(client, "latitude"),
    )
    db.commit()
    db.refresh(client)
    return client


@router.delete("/{client_id}")
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Eliminar cliente (solo admin). Rechaza si tiene pedidos asociados."""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if db.query(Order).filter(Order.client_id == client_id).first():
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar: tiene pedidos asociados",
        )
    db.delete(client)
    db.commit()
    return {"detail": "Cliente eliminado"}