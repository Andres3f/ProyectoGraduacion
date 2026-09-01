from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Base de datos ──────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql://optirutas:optirutas_secret@db:5432/optirutas_jalapa"
    )

    # ── JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = "super-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── App ────────────────────────────────────────────────────
    APP_NAME: str = "Optirutas Jalapa"
    DEBUG: bool = True

    # ── CORS (OPT-20) ──────────────────────────────────────────
    # Orígenes permitidos separados por coma en la variable de entorno
    # FRONTEND_ORIGINS. Para producción se debe apuntar al dominio real del
    # frontend; nunca usar "*" con allow_credentials=True.
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── Optimizador / geografía (Sprint 3) ─────────────────────
    # Depósito base (centro de Jalapa, GT).
    DEPOT_LAT: float = 14.6347
    DEPOT_LNG: float = -89.9889
    # Velocidad promedio urbana (km/h) usada para estimar tiempos de viaje
    # a partir de la distancia.
    AVERAGE_SPEED_KMH: float = 30.0
    # Factor de corrección de caminos: multiplica la distancia en línea
    # recta (Haversine) para aproximar la distancia real por calle.
    ROAD_DISTANCE_FACTOR: float = 1.3
    # Tiempo máximo de trabajo por vehículo al día (minutos).
    MAX_TIME_PER_VEHICLE_MIN: int = 24 * 60
    # Hora de salida nominal del depósito (HH:MM local). Se usa para
    # estimar ETA de cada parada.
    DEPOT_DEPARTURE: str = "08:00"
    # Costo por kilómetro recorrido (GTQ) para métricas de ahorro.
    COST_PER_KM_GTQ: float = 12.0

    # ── Ahorro estimado (PG-22) ────────────────────────────────
    # Parámetros para estimar el ahorro de combustible y costo operativo.
    FUEL_CONSUMPTION_KM_PER_LITER: float = 8.0  # rendimiento promedio del camión
    FUEL_PRICE_GTQ_PER_LITER: float = 28.0
    DRIVER_COST_GTQ_PER_HOUR: float = 35.0

    # ── OpenRouteService (opcional) ─────────────────────────────
    # Si ORS_API_KEY está vacío, el sistema usa Haversine automáticamente.
    ORS_API_KEY: str = ""
    ORS_BASE_URL: str = "https://api.openrouteservice.org"
    ORS_PROFILE: str = "driving-hgv"  # vehículo pesado (camión)
    ORS_TIMEOUT_SECONDS: float = 8.0

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
