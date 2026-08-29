import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.routers import auth, users, orders, vehicles, routes, clients
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

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
app.include_router(clients.router)


@app.get("/health", tags=["Sistema"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}
