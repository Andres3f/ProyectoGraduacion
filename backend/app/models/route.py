import enum

from sqlalchemy import (
    Column, Integer, String, Float, Enum, DateTime, ForeignKey, JSON, func,
)
from app.database import Base


class RouteStatus(str, enum.Enum):
    planificada = "planificada"
    en_progreso = "en_progreso"
    completada = "completada"
    cancelada = "cancelada"


class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    stops = Column(JSON, nullable=True)  # Lista ordenada de order_ids
    total_distance_km = Column(Float, nullable=True)
    total_duration_min = Column(Float, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    status = Column(
        Enum(RouteStatus), nullable=False, default=RouteStatus.planificada
    )
    optimized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
