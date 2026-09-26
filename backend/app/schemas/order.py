from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional
from datetime import datetime
from app.models.order import OrderStatus

# Una ventana de tiempo se almacena como minutos desde las 00:00. La interfaz
# la captura y muestra en formato HH:MM (ej. "14:00" -> 840, "16:00" -> 960).
MINUTES_PER_DAY = 24 * 60

# Rango válido de una hora del día en minutos: 0 (00:00) a 1440 (24:00).
_MINUTES_FIELD = Field(default=None, ge=0, le=MINUTES_PER_DAY)


class OrderCreate(BaseModel):
    """Datos de entrada para crear un pedido; el snapshot del cliente
    (nombre, dirección, coordenadas) se copia automáticamente desde el cliente."""
    client_id: int
    weight_kg: float = Field(0, ge=0)
    volume_m3: float = Field(0, ge=0)
    # Ventana de entrega deseada, en minutos desde las 00:00.
    # Ej. 480 = 08:00 y 960 = 16:00. Nulos = sin restricción de horario.
    time_window_start: Optional[int] = _MINUTES_FIELD
    time_window_end: Optional[int] = _MINUTES_FIELD
    service_time_min: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _check_time_window(self):
        start, end = self.time_window_start, self.time_window_end
        if start is not None and end is not None and end <= start:
            raise ValueError(
                "La hora de fin de la ventana de entrega debe ser posterior "
                "a la hora de inicio."
            )
        return self


class OrderUpdate(BaseModel):
    """Edición parcial de un pedido (incluye cambio de estado/entrega)."""
    client_id: Optional[int] = None
    weight_kg: Optional[float] = Field(default=None, ge=0)
    volume_m3: Optional[float] = Field(default=None, ge=0)
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    """Respuesta API de un pedido con su snapshot de cliente y métricas de carga."""
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
    # Ventana de entrega en minutos desde las 00:00 (la UI la muestra HH:MM).
    time_window_start: Optional[int]
    time_window_end: Optional[int]
    service_time_min: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)