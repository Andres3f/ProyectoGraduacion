from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.order import OrderStatus


class OrderCreate(BaseModel):
    client_name: str
    address: str
    latitude: float
    longitude: float
    weight_kg: float = 0
    volume_m3: float = 0
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    client_name: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    weight_kg: Optional[float] = None
    volume_m3: Optional[float] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: int
    client_name: str
    address: str
    latitude: float
    longitude: float
    weight_kg: float
    volume_m3: float
    status: OrderStatus
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
