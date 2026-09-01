from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.route import Route, RouteStatus
from app.models.route_stop import RouteStop
from app.models.user import User, RoleEnum
from app.auth.dependencies import require_role

router = APIRouter(prefix="/api/route-stops", tags=["Paradas de ruta"])

VALID_STATUSES = {"entregado", "fallido"}


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
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail="Estado inválido (usa 'entregado' o 'fallido')"
        )

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

    stop.status = status
    stop.delivered_at = func.now() if status == "entregado" else None
    db.add(stop)
    db.flush()

    # Si todas las paradas de la ruta están resueltas, la ruta se completa.
    route = stop.route
    if route and all(
        s.status in ("entregado", "fallido") for s in route.stops
    ):
        route.status = RouteStatus.completada
        db.add(route)

    db.commit()
    from app.services.audit import log_action

    log_action(
        db, current_user.id, "marcar_entrega",
        entidad="route_stop", entidad_id=stop_id,
        detalle={"status": status},
    )
    db.commit()
    return {"detail": "Estado actualizado"}
