from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.route import RouteStatus


class RouteCreate(BaseModel):
    name: Optional[str] = None
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    order_ids: List[int] = []


class RouteStopOut(BaseModel):
    id: int
    order_id: int
    sequence: int
    eta: Optional[datetime] = None
    distance_from_previous_km: Optional[float] = None
    status: str
    delivered_at: Optional[datetime] = None
    client_name: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    weight_kg: float = 0.0

    model_config = ConfigDict(from_attributes=True)


class RouteOut(BaseModel):
    id: int
    name: Optional[str]
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    stops: List[RouteStopOut] = []
    total_distance_km: Optional[float]
    total_duration_min: Optional[float]
    total_weight_kg: Optional[float]
    status: RouteStatus
    optimized_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Optimización (OPT-11) ─────────────────────────────────────


class OptimizeRequest(BaseModel):
    order_ids: List[int]
    vehicle_ids: List[int]


class OptimizeResponse(BaseModel):
    routes: List[RouteOut] = []
    unassigned_order_ids: List[int] = []
    success: bool
    message: Optional[str] = None
    metrics: Optional[dict] = None
