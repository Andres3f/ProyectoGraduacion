from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import RoleEnum


# ── Request ───────────────────────────────────────────────────
class UserCreate(BaseModel):
    """Datos de entrada para crear un usuario (el password se hashea)."""
    email: EmailStr
    full_name: str
    password: str
    role: RoleEnum = RoleEnum.conductor


class UserUpdate(BaseModel):
    """Edición parcial de un usuario (rol, nombre, alta/baja)."""
    full_name: Optional[str] = None
    role: Optional[RoleEnum] = None
    is_active: Optional[bool] = None


# ── Response ──────────────────────────────────────────────────
class UserOut(BaseModel):
    """Respuesta API de un usuario; nunca expone el password."""
    id: int
    email: str
    full_name: str
    role: RoleEnum
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
