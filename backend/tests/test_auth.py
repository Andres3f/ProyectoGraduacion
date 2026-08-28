"""Tests de autenticación JWT + refresh + RBAC (OPT-5)."""


def test_register_success(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "nueva.cuenta@optirutas.com",
            "full_name": "Nueva Cuenta",
            "password": "Passw0rd!",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_register_duplicate_email(client):
    payload = {
        "email": "duplicado@optirutas.com",
        "full_name": "Duplicado",
        "password": "Passw0rd!",
    }
    assert client.post("/api/auth/register", json=payload).status_code == 200
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_success_returns_token_pair(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "login@optirutas.com",
            "full_name": "Para Login",
            "password": "Passw0rd!",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login@optirutas.com", "password": "Passw0rd!"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "noexiste@optirutas.com", "password": "incorrecta"},
    )
    assert resp.status_code == 401


def test_refresh_valid(client):
    client.post(
        "/api/auth/register",
        json={
            "email": "refresh@optirutas.com",
            "full_name": "Para Refresh",
            "password": "Passw0rd!",
        },
    )
    login = client.post(
        "/api/auth/login",
        json={"email": "refresh@optirutas.com", "password": "Passw0rd!"},
    ).json()
    resp = client.post(
        "/api/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]
    assert resp.json()["refresh_token"]


def test_refresh_invalid(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "token-invalido"})
    assert resp.status_code == 401


def test_logout(client, admin_headers):
    resp = client.post("/api/auth/logout", headers=admin_headers)
    assert resp.status_code == 204


def test_rbac_forbidden_for_conductor(client, regular_user_headers):
    """Access token de un conductor no puede usar endpoints de admin."""
    resp = client.post(
        "/api/users",
        json={
            "email": "intento@optirutas.com",
            "full_name": "Intento",
            "password": "Passw0rd!",
        },
        headers=regular_user_headers,
    )
    assert resp.status_code == 403


def test_me_endpoint(client, admin_headers):
    resp = client.get("/api/users/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@optirutas.com"