"""
Seed inicial: crea un usuario administrador si no existe ninguno.
Se ejecuta automáticamente al arrancar la aplicación.
"""

import logging

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.user import User, RoleEnum
from app.auth.passwords import hash_password

logger = logging.getLogger(__name__)

# ── Credenciales por defecto del admin ─────────────────────────
ADMIN_EMAIL = "admin@optirutas.com"
ADMIN_PASSWORD = "Admin123!"
ADMIN_NAME = "Administrador"


def create_initial_admin() -> None:
    """Crea el usuario admin si la tabla users está vacía o no existe un admin."""
    db: Session = SessionLocal()
    try:
        # Verificar si ya existe algún admin
        existing_admin = (
            db.query(User).filter(User.role == RoleEnum.admin).first()
        )
        if existing_admin:
            logger.info("✅ Ya existe un usuario admin (%s). Seed omitido.", existing_admin.email)
            return

        admin = User(
            email=ADMIN_EMAIL,
            full_name=ADMIN_NAME,
            hashed_password=hash_password(ADMIN_PASSWORD),
            role=RoleEnum.admin,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        logger.info("🌱 Usuario admin creado: %s / %s", ADMIN_EMAIL, ADMIN_PASSWORD)
    except Exception as e:
        db.rollback()
        logger.warning("⚠️ No se pudo crear el admin (¿tablas aún no existen?): %s", e)
    finally:
        db.close()
