from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.route import RouteStatus


class RouteCreate(BaseModel):
    """Entrada para crear una ruta a partir de pedidos seleccionados."""
    name: Optional[str] = None
    vehicle_id: Optional[int] = None
    driver_id: Optional[int] = None
    # Pedidos que conformarán la ruta; su orden se resuelve al optimizar.
    order_ids: List[int] = []


class RouteStopOut(BaseModel):
    """Respuesta API de una parada: datos de entrega + denormalizados del pedido
    para el mapa y el frontend del conductor (OPT-18)."""
    id: int
    order_id: int
    sequence: int
    eta: Optional[datetime] = None
    distance_from_previous_km: Optional[float] = None
    status: str
    delivered_at: Optional[datetime] = None
    client_name: str = ""
    address: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    weight_kg: float = 0.0
    # Notas de entrega del pedido: instrucciones de acceso, contacto, etc.
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class RouteOut(BaseModel):
    """Respuesta API de una ruta completa: paradas en orden, métricas totales,
    geometría real y pasos de navegación por tramo."""
    id: int
    name: Optional[str]
    vehicle_id: Optional[int]
    driver_id: Optional[int]
    depot_id: Optional[int] = None
    stops: List[RouteStopOut] = []
    # Geometría del trayecto de ida (depósito -> última parada).
    route_geometry: Optional[dict] = None
    # Geometría del trayecto de regreso (última parada -> depósito). El mapa la
    # dibuja en otro color para distinguirla de la ida.
    route_geometry_return: Optional[dict] = None
    steps: Optional[List[dict]] = None
    total_distance_km: Optional[float]
    total_duration_min: Optional[float]
    total_weight_kg: Optional[float]
    distance_source: Optional[str] = "haversine"
    status: RouteStatus
    optimized_at: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Optimización (OPT-11) ─────────────────────────────────────


class AssignDriverRequest(BaseModel):
    """Asigna un conductor a una ruta."""
    driver_id: int


class OptimizeRequest(BaseModel):
    """Solicitud de optimización: pedidos a repartir y vehículos disponibles."""
    order_ids: List[int]
    vehicle_ids: List[int]


class OptimizeResponse(BaseModel):
    """Resultado de la optimización: las rutas generadas, pedidos que no se
    pudieron asignar, y métricas del proceso."""
    routes: List[RouteOut] = []
    unassigned_order_ids: List[int] = []
    success: bool
    message: Optional[str] = None
    metrics: Optional[dict] = None
    matrix_source: Optional[str] = None  # "ors" (distancias reales) | "haversine"
