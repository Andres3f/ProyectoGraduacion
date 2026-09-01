from typing import List
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User, RoleEnum
from app.schemas.audit import AuditLogOut
from app.auth.dependencies import require_role

router = APIRouter(prefix="/api/logs", tags=["Auditoría"])


@router.get("", response_model=List[AuditLogOut])
def list_logs(
    accion: str | None = Query(None, description="Filtrar por acción (ej: optimizar_rutas)"),
    user_id: int | None = Query(None, description="Filtrar por usuario"),
    date_from: date | None = Query(None, description="Fecha inicial (YYYY-MM-DD)"),
    date_to: date | None = Query(None, description="Fecha final (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Consulta los logs de auditoría (solo admin)."""
    query = db.query(AuditLog)
    if accion:
        query = query.filter(AuditLog.accion == accion)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if date_from:
        query = query.filter(AuditLog.created_at >= date_from)
    if date_to:
        query = query.filter(AuditLog.created_at <= date_to)
    return query.order_by(AuditLog.created_at.desc()).limit(200).all()
