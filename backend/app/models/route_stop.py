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

    order = relationship("Order")
