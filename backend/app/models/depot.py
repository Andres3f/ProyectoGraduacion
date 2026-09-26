from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, func
from geoalchemy2 import Geography
from app.database import Base


class Depot(Base):
    """Punto de partida de los camiones (patio/bodega) para el reparto.

    Cada vehículo puede tener su propio depósito; si no tiene uno asignado
    (depot_id NULL), usa el depósito marcado como `is_default`.
    """

    __tablename__ = "depots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )