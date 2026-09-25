import enum

from sqlalchemy import Column, Integer, String, Enum, Boolean, DateTime, func
from app.database import Base


class RoleEnum(str, enum.Enum):
    """Roles del sistema que determinan los permisos de acceso del usuario."""
    admin = "admin"
    planificador = "planificador"
    conductor = "conductor"
    gerente = "gerente"


class User(Base):
    """Usuario del sistema (planificadores, conductores, gerentes y admins)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.conductor)
    # Baja lógica: los usuarios desactivados no pueden iniciar sesión.
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
