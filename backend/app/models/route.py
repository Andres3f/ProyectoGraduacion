import enum

from sqlalchemy import (
    Column, Integer, String, Float, Enum, DateTime, ForeignKey, JSON, func,
)
from sqlalchemy.orm import relationship
from app.database import Base


class RouteStatus(str, enum.Enum):
    """Estado del recorrido planificado/ejecutado de un vehículo."""
    planificada = "planificada"
    en_progreso = "en_progreso"
    completada = "completada"
    cancelada = "cancelada"


class Route(Base):
    """Ruta de reparto: conjunto ordenado de paradas que un vehículo recorre
    para entregar los pedidos asignados por el optimizador."""

    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=True)
    # Vehículo y conductor asignados a esta ruta.
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=True)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # Depósito desde el que salió realmente esta ruta (para dibujo en mapa y
    # reportes históricos aunque luego cambie el depósito por defecto).
    depot_id = Column(Integer, ForeignKey("depots.id"), nullable=True)
    # Snapshot JSON de las paradas (orden de order_ids). Se conserva un sprint
    # más por compatibilidad con el frontend viejo; se eliminará en Sprint 4
    # cuando el frontend lea exclusivamente de la relación `stops`.
    stops_snapshot = Column("stops", JSON, nullable=True)
    total_distance_km = Column(Float, nullable=True)
    total_duration_min = Column(Float, nullable=True)
    total_weight_kg = Column(Float, nullable=True)
    # Fuente de las distancias de la ruta: "ors" (distancias reales por
    # carretera) o "haversine" (estimación en línea recta corregida).
    distance_source = Column(String(20), nullable=True, default="haversine")
    status = Column(
        Enum(RouteStatus), nullable=False, default=RouteStatus.planificada
    )
    # Timestamp en que se ejecutó la optimización que generó esta ruta.
    optimized_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Geometría real por carretera (GeoJSON LineString de ORS) + instrucciones
    # de manejo por tramo. None si no se pudo obtener (fallback línea recta).
    # Se guarda separada por trayecto para poder dibujarlas con colores
    # distintos: `route_geometry` es la ida (depósito -> última parada) y
    # `route_geometry_return` el regreso (última parada -> depósito).
    route_geometry = Column(JSON, nullable=True)
    route_geometry_return = Column(JSON, nullable=True)
    steps = Column(JSON, nullable=True)

    # Paradas relacionadas (tabla route_stops), ordenadas por secuencia.
    # `RouteOut.stops` se puebla desde aquí (no desde el JSON).
    stops = relationship(
        "RouteStop", order_by="RouteStop.sequence", back_populates="route",
        cascade="all, delete-orphan"
    )
