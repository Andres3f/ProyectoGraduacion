from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional
import re
from app.models.vehicle import VehicleStatus


# Placas de Guatemala: 1-3 letras + 3-4 dígitos (ej. "P-1234", "C-4567").
PLATE_REGEX = r"^[A-Z]{1,3}-?\d{3,4}$"


class VehicleCreate(BaseModel):
    plate: str
    description: Optional[str] = None
    capacity_kg: float = Field(10000, gt=0)
    capacity_m3: float = Field(20, gt=0)
    driver_id: Optional[int] = None

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(PLATE_REGEX, v):
            raise ValueError(
                "Formato de placa inválido. Ejemplos válidos: P-123, C-4567"
            )
        return v


class VehicleUpdate(BaseModel):
    plate: Optional[str] = None
    description: Optional[str] = None
    capacity_kg: Optional[float] = Field(default=None, gt=0)
    capacity_m3: Optional[float] = Field(default=None, gt=0)
    status: Optional[VehicleStatus] = None
    is_active: Optional[bool] = None
    driver_id: Optional[int] = None

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip().upper()
        if not re.match(PLATE_REGEX, v):
            raise ValueError(
                "Formato de placa inválido. Ejemplos válidos: P-123, C-4567"
            )
        return v


class VehicleOut(BaseModel):
    id: int
    plate: str
    description: Optional[str]
    capacity_kg: float
    capacity_m3: float
    status: VehicleStatus
    is_active: bool
    driver_id: Optional[int]

    model_config = ConfigDict(from_attributes=True)