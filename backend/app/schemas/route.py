from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.route import RouteStatus


class RouteCreate(BaseModel):
    name: Optional[str] = None
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    order_ids: List[int] = []


class RouteOut(BaseModel):
    id: int
    name: Optional[str]
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    stops: Optional[list]
    total_distance_km: Optional[float]
    total_duration_min: Optional[float]
    total_weight_kg: Optional[float]
    status: RouteStatus
    optimized_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
