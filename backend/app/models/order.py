import enum

from sqlalchemy import (
    Column, Integer, String, Float, Enum, DateTime, ForeignKey, func,
)
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from app.database import Base


class OrderStatus(str, enum.Enum):
    pendiente = "pendiente"
    asignado = "asignado"
    en_ruta = "en_ruta"
    entregado = "entregado"
    cancelado = "cancelado"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    # Columnas denormalizadas (snapshot del cliente) para no romper el
    # frontend ni el optimizador. Se mantienen sincronizadas con el cliente.
    client_name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    weight_kg = Column(Float, nullable=False, default=0)
    volume_m3 = Column(Float, nullable=False, default=0)
    status = Column(
        Enum(OrderStatus), nullable=False, default=OrderStatus.pendiente
    )
    # Ventana de tiempo de entrega deseada, en minutos desde las 00:00.
    # Ej. 540 = 09:00, 720 = 12:00. Nullable = sin restricción de horario.
    time_window_start = Column(Integer, nullable=True)
    time_window_end = Column(Integer, nullable=True)
    # Tiempo estimado de servicio en la entrega (minutos).
    service_time_min = Column(Integer, nullable=True, default=15)
    notes = Column(String(1000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    client = relationship("Client")
