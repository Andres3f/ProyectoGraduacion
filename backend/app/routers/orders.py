from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import Order
from app.models.client import Client
from app.models.user import User, RoleEnum
from app.schemas.order import OrderCreate, OrderUpdate, OrderOut
from app.auth.dependencies import get_current_user, require_role
from app.services.geo import point_wkt

router = APIRouter(prefix="/api/orders", tags=["Pedidos"])


def _snapshot_from_client(client: Client) -> dict:
    """Construye el snapshot denormalizado de un pedido a partir de su cliente."""
    return {
        "client_name": client.name,
        "address": client.address,
        "latitude": client.latitude,
        "longitude": client.longitude,
        "geom": point_wkt(client.longitude, client.latitude),
    }


def _get_client_or_400(db: Session, client_id: int) -> Client:
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=400, detail="El cliente no existe")
    return client


@router.get("/", response_model=List[OrderOut])
@router.get("", response_model=List[OrderOut], include_in_schema=False)
def list_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Listar pedidos."""
    return db.query(Order).all()


@router.post("/", response_model=OrderOut)
def create_order(
    order_in: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Crear pedido (admin y planificador)."""
    client = _get_client_or_400(db, order_in.client_id)
    order = Order(
        **order_in.model_dump(),
        **_snapshot_from_client(client),
        created_by=current_user.id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.post("/upload")
async def upload_orders(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Carga masiva de pedidos desde CSV o Excel.

    Columnas requeridas: ``client_id``, ``weight_kg``, ``volume_m3``.
    La operación es atómica: si alguna fila es inválida, no se crea ningún
    pedido y se devuelven los errores de cada fila.
    """
    import math

    import pandas as pd
    from io import BytesIO

    content = await file.read()
    filename = (file.filename or "").lower()
    if filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(content))
    elif filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(content))
    else:
        raise HTTPException(
            status_code=400, detail="Formato no soportado (usa .csv o .xlsx)"
        )

    required_cols = {"client_id", "weight_kg", "volume_m3"}
    missing = required_cols - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400, detail=f"Faltan columnas: {sorted(missing)}"
        )

    errors = []
    valid_orders = []
    for idx, row in df.iterrows():
        row_num = idx + 2  # fila + encabezado, para reportar como en Excel
        client_id = int(row["client_id"])
        client = db.query(Client).filter(Client.id == client_id).first()
        if not client:
            errors.append(f"Fila {row_num}: cliente {client_id} no existe")
            continue
        weight = row["weight_kg"]
        volume = row.get("volume_m3", 0)
        if isinstance(weight, float) and math.isnan(weight):
            errors.append(f"Fila {row_num}: weight_kg es requerido")
            continue
        if weight <= 0:
            errors.append(f"Fila {row_num}: weight_kg debe ser > 0")
            continue
        if isinstance(volume, float) and math.isnan(volume):
            volume = 0
        if volume < 0:
            errors.append(f"Fila {row_num}: volume_m3 no puede ser negativo")
            continue
        valid_orders.append(
            Order(
                client_id=client.id,
                weight_kg=float(weight),
                volume_m3=float(volume),
                **_snapshot_from_client(client),
                created_by=current_user.id,
            )
        )

    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    # Transacción atómica: todo o nada
    db.add_all(valid_orders)
    db.commit()
    return {"created": len(valid_orders)}


@router.get("/{order_id}", response_model=OrderOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    return order


@router.put("/{order_id}", response_model=OrderOut)
def update_order(
    order_id: int,
    order_in: OrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_role([RoleEnum.admin, RoleEnum.planificador])
    ),
):
    """Actualizar pedido. Si cambia el cliente, refresca el snapshot."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    data = order_in.model_dump(exclude_unset=True)
    client_id = data.get("client_id")
    if client_id is not None and client_id != order.client_id:
        client = _get_client_or_400(db, client_id)
        data.update(_snapshot_from_client(client))
    for field, value in data.items():
        setattr(order, field, value)
    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Eliminar pedido (solo admin)."""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    db.delete(order)
    db.commit()
    return {"detail": "Pedido eliminado"}
