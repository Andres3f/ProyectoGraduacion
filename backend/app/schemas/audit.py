from datetime import datetime
from typing import Optional, List, Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    accion: str
    entidad: Optional[str] = None
    entidad_id: Optional[int] = None
    detalle: Optional[dict] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
