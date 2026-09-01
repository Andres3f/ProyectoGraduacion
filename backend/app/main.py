import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import (
    auth, users, orders, vehicles, routes, route_stops, clients, dashboard, audit,
)
from app.seed import create_initial_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan: crear tablas + seed ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Iniciando %s …", settings.APP_NAME)
    # Importar todos los modelos para que Base.metadata los conozca
    import app.models.user  # noqa: F401
    import app.models.order  # noqa: F401
    import app.models.vehicle  # noqa: F401
    import app.models.route  # noqa: F401
    import app.models.route_stop  # noqa: F401
    import app.models.client  # noqa: F401
    import app.models.audit_log  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("✅ Tablas de la BD creadas / verificadas")

    create_initial_admin()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="API de optimización de rutas de cemento en Jalapa",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS (OPT-20) ─────────────────────────────────────────────
# Orígenes permitidos desde config/entorno. El backend no usa "*" en
# producción: cada origen explícito permite credenciales de forma segura.
_frontend_origins = [
    o.strip()
    for o in settings.FRONTEND_ORIGINS.split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(orders.router)
app.include_router(vehicles.router)
app.include_router(routes.router)
app.include_router(route_stops.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(audit.router)


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
