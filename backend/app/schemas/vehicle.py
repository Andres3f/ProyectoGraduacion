from pydantic import BaseModel
from typing import Optional
from app.models.vehicle import VehicleStatus


class VehicleCreate(BaseModel):
    plate: str
    description: Optional[str] = None
    capacity_kg: float = 10000
    capacity_m3: float = 20


class VehicleUpdate(BaseModel):
    description: Optional[str] = None
    capacity_kg: Optional[float] = None
    capacity_m3: Optional[float] = None
    status: Optional[VehicleStatus] = None
    is_active: Optional[bool] = None


class VehicleOut(BaseModel):
    id: int
    plate: str
    description: Optional[str]
    capacity_kg: float
    capacity_m3: float
    status: VehicleStatus
    is_active: bool

    class Config:
        from_attributes = True
