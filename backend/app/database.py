from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# Motor SQLAlchemy; echo activa los logs SQL en modo debug.
engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
# Fábrica de sesiones (no inicia transacción ni autoflush automáticamente).
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependencia FastAPI que inyecta una sesión de BD."""
    db = SessionLocal()
    try:
        yield db
    finally:
        # La sesión siempre se cierra tras el request (y se descartan cambios sin commit).
        db.close()
