from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    client_id: int
    weight_kg: float = Field(0, ge=0)
    volume_m3: float = Field(0, ge=0)
    time_window_start: Optional[int] = None
    time_window_end: Optional[int] = None
    service_time_min: Optional[int] = None
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    client_id: Optional[int] = None
    weight_kg: Optional[float] = Field(default=None, ge=0)
    volume_m3: Optional[float] = Field(default=None, ge=0)
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    client_id: int
    # Snapshot denormalizado del cliente (mantiene compatibilidad con el
    # frontend y el optimizador, que leen estos campos directamente).
    client_name: str
    address: str
    latitude: float
    longitude: float
    weight_kg: float
    volume_m3: float
    status: OrderStatus
    time_window_start: Optional[int]
    time_window_end: Optional[int]
    service_time_min: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)