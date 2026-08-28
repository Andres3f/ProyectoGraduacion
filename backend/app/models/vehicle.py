import enum

from sqlalchemy import (
    Column, Integer, String, Float, Enum, Boolean, DateTime, ForeignKey, func,
)
from app.database import Base


class VehicleStatus(str, enum.Enum):
    disponible = "disponible"
    en_ruta = "en_ruta"
    mantenimiento = "mantenimiento"


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(20), unique=True, nullable=False)
    description = Column(String(255), nullable=True)
    capacity_kg = Column(Float, nullable=False, default=10000)
    capacity_m3 = Column(Float, nullable=False, default=20)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(
        Enum(VehicleStatus), nullable=False, default=VehicleStatus.disponible
    )
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
