from sqlalchemy import (
    Column, Integer, Float, String, DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class RouteStop(Base):
    __tablename__ = "route_stops"

    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(Integer, ForeignKey("routes.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    eta = Column(DateTime(timezone=True), nullable=True)
    distance_from_previous_km = Column(Float, nullable=True)
    status = Column(
        String(20), nullable=False, default="pendiente"
    )  # pendiente/entregado/fallido — lo usará OPT-19
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    order = relationship("Order")
    route = relationship("Route", back_populates="stops")

    # Datos denormalizados del cliente/pedido para exposición API (OPT-18):
    # el frontend del conductor y el mapa los leen desde aquí, sin consultas
    # extra. Se resuelven desde la relación `order`.
    @property
    def client_name(self) -> str:
        return self.order.client_name if self.order else ""

    @property
    def address(self) -> str:
        return self.order.address if self.order else ""

    @property
    def latitude(self) -> float:
        return self.order.latitude if self.order else 0.0

    @property
    def longitude(self) -> float:
        return self.order.longitude if self.order else 0.0

    @property
    def weight_kg(self) -> float:
        return self.order.weight_kg if self.order else 0.0
