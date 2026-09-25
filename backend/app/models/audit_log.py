from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class AuditLog(Base):
    """Registro de auditoría del sistema: traza las acciones sensibles de los
    usuarios (creación de pedidos, optimización de rutas, etc.)."""

    __tablename__ = "logs_sistema"

    id = Column(Integer, primary_key=True, index=True)
    # Usuario que ejecutó la acción; Nullable para eventos del sistema.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    accion = Column(String(100), nullable=False)       # "crear_pedido", "optimizar_rutas", etc.
    entidad = Column(String(50), nullable=True)        # "order", "route", "user", ...
    # Id de la entidad afectada (nullable: acciones globales sin registro concreto).
    entidad_id = Column(Integer, nullable=True)
    detalle = Column(JSONB, nullable=True)             # payload libre (antes/después, ids afectados)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
