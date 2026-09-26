from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.order import OrderStatus
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User, RoleEnum
from app.auth.dependencies import require_role

router = APIRouter(prefix="/api/route-stops", tags=["Paradas de ruta"])

VALID_STATUSES = {"entregado", "fallido"}


# Acción de campo del conductor: registra el resultado de la entrega de una
# parada de SU ruta. El rol conductor es obligatorio.
@router.put("/{stop_id}/status")
def update_stop_status(
    stop_id: int,
    status: str = Query(..., description="entregado | fallido"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.conductor])),
):
    """Marca una parada como entregada o fallida (solo el conductor dueño).

    Un conductor solo puede actualizar paradas de sus propias rutas; cualquier
    otra parada devuelve 404 para no filtrar información ajena.
    """
    # Valida que el estado llegue entre los permitidos por el sistema.
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail="Estado inválido (usa 'entregado' o 'fallido')"
        )

    # Restringe la parada a las rutas cuyo driver es el usuario autenticado.
    stop = (
        db.query(RouteStop)
        .join(Route)
        .filter(
            RouteStop.id == stop_id,
            Route.driver_id == current_user.id,
        )
        .first()
    )
    if not stop:
        raise HTTPException(
            status_code=404,
            detail="Parada no encontrada o no te pertenece",
        )

    from sqlalchemy import func

    # Solo una entrega registra timestamp; una fallida lo limpia.
    stop.status = status
    stop.delivered_at = func.now() if status == "entregado" else None

    # Sincroniza el estado del pedido con el resultado registrado por el
    # conductor. Sin esto, la lista de pedidos y el dashboard seguirían
    # mostrando "en_ruta" aunque la entrega ya fue resuelta.
    if stop.order:
        target = (
            OrderStatus.entregado if status == "entregado" else OrderStatus.fallido
        )
        stop.order.status = target
        db.add(stop.order)

    db.add(stop)
    db.flush()

    # Cuando todas las paradas quedan resueltas la ruta aún NO se completa:
    # el camión sigue en camino de retorno al depósito. Pasa a `en_progreso`
    # y el conductor confirma el regreso con `PUT /api/routes/{id}/complete`,
    # que es lo que marca la ruta como `completada`.
    route = stop.route
    if route and all(
        s.status in ("entregado", "fallido") for s in route.stops
    ):
        route.status = RouteStatus.en_progreso
        db.add(route)

    db.commit()
    from app.services.audit import log_action

    # Audita el marcado de la entrega con su estado final.
    log_action(
        db, current_user.id, "marcar_entrega",
        entidad="route_stop", entidad_id=stop_id,
        detalle={"status": status},
    )
    db.commit()
    return {"detail": "Estado actualizado"}
