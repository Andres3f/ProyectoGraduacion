from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: int | None,
    accion: str,
    entidad: str | None = None,
    entidad_id: int | None = None,
    detalle: dict | None = None,
) -> None:
    """Registra una acción de auditoría. No lanza excepción si falla —
    un problema de logging nunca debe tumbar la operación principal."""
    try:
        db.add(AuditLog(
            user_id=user_id, accion=accion, entidad=entidad,
            entidad_id=entidad_id, detalle=detalle,
        ))
        # No hacemos commit aquí: se une a la misma transacción del
        # endpoint que la llama, así que si el endpoint falla, el log
        # tampoco se persiste (consistencia).
    except Exception:
        pass
