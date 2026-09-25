from sqlalchemy import Column, Integer, String, Float, DateTime, func
from geoalchemy2 import Geography

from app.database import Base


class Client(Base):
    """Cliente o punto de entrega: destino físico al que se despachan los
    pedidos, con su ubicación geográfica para la optimización de rutas."""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    zone = Column(String(100), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    # Punto geográfico PostGIS (4326) derivado de lat/long para consultas espaciales.
    geom = Column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )