"""
Configuración compartida de pytest.

Usa una base de datos PostgreSQL dedicada (optirutas_jalapa_test) para no
contaminar la base de desarrollo. Antes de importar la app se fuerza
``DATABASE_URL`` vía variable de entorno (pydantic-settings le da prioridad
sobre el archivo .env).
"""

import os

os.environ["DATABASE_URL"] = (
    "postgresql+psycopg2://optirutas:optirutas_secret@localhost:5432/optirutas_jalapa_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ["DEBUG"] = "false"

import pytest
from fastapi.testclient import TestClient

# Importar modelos para que Base.metadata los conozca
from app.database import Base, engine  # noqa: E402
import app.models.user  # noqa: E402,F401
import app.models.order  # noqa: E402,F401
import app.models.vehicle  # noqa: E402,F401
import app.models.route  # noqa: E402,F401
import app.models.route_stop  # noqa: E402,F401

from app.main import app  # noqa: E402
from app.seed import create_initial_admin  # noqa: E402

ADMIN_EMAIL = "admin@optirutas.com"
ADMIN_PASSWORD = "Admin123!"


@pytest.fixture(scope="session")
def client():
    """TestClient contra la BD de pruebas."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _reset_db():
    """Deja la BD limpia antes de cada test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    create_initial_admin()
    yield


def _auth_headers(client, email, password):
    resp = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers(client):
    return _auth_headers(client, ADMIN_EMAIL, ADMIN_PASSWORD)


@pytest.fixture
def regular_user_headers(client):
    """Crea un usuario conductor vía registro y devuelve sus headers."""
    email = "usuario.test@optirutas.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "full_name": "Usuario Test", "password": "Passw0rd!"},
    )
    assert resp.status_code == 200, resp.text
    return _auth_headers(client, email, "Passw0rd!")


def _create_user_with_role(client, admin_headers, email, role):
    resp = client.post(
        "/api/users",
        json={
            "email": email,
            "full_name": f"{role.capitalize()} Test",
            "password": "Passw0rd!",
            "role": role,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.fixture
def planner_headers(client, admin_headers):
    email = "planner.test@optirutas.com"
    _create_user_with_role(client, admin_headers, email, "planificador")
    return _auth_headers(client, email, "Passw0rd!")


@pytest.fixture
def conductor_headers(client, admin_headers):
    email = "driver.test@optirutas.com"
    _create_user_with_role(client, admin_headers, email, "conductor")
    return _auth_headers(client, email, "Passw0rd!")