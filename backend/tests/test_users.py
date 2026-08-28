"""Tests del CRUD de usuarios (OPT-6)."""


def _create_user(client, admin_headers, email="nuevo@optirutas.com", role="conductor"):
    return client.post(
        "/api/users",
        json={
            "email": email,
            "full_name": "Usuario Nuevo",
            "password": "Passw0rd!",
            "role": role,
        },
        headers=admin_headers,
    )


def test_create_user_admin(client, admin_headers):
    resp = _create_user(client, admin_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "nuevo@optirutas.com"
    assert body["role"] == "conductor"
    assert body["is_active"] is True


def test_create_user_duplicate_email(client, admin_headers):
    _create_user(client, admin_headers, email="dup@optirutas.com")
    resp = _create_user(client, admin_headers, email="dup@optirutas.com")
    assert resp.status_code == 400


def test_create_user_forbidden_for_non_admin(client, regular_user_headers):
    resp = _create_user(client, regular_user_headers)
    assert resp.status_code == 403


def test_list_users(client, admin_headers):
    resp = client.get("/api/users", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_user_by_id(client, admin_headers):
    created = _create_user(
        client, admin_headers, email="detalle@optirutas.com"
    ).json()
    resp = client.get(f"/api/users/{created['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "detalle@optirutas.com"


def test_get_user_by_id_forbidden(client, regular_user_headers):
    resp = client.get("/api/users/1", headers=regular_user_headers)
    assert resp.status_code == 403


def test_get_user_not_found(client, admin_headers):
    resp = client.get("/api/users/99999", headers=admin_headers)
    assert resp.status_code == 404


def test_update_user_role(client, admin_headers):
    created = _create_user(
        client, admin_headers, email="cambio-rol@optirutas.com"
    ).json()
    resp = client.put(
        f"/api/users/{created['id']}",
        json={"role": "planificador"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "planificador"


def test_deactivate_user_soft_delete(client, admin_headers):
    created = _create_user(
        client, admin_headers, email="desactivar@optirutas.com"
    ).json()
    resp = client.delete(f"/api/users/{created['id']}", headers=admin_headers)
    assert resp.status_code == 200
    detail = client.get(f"/api/users/{created['id']}", headers=admin_headers)
    assert detail.status_code == 200
    assert detail.json()["is_active"] is False


def test_cannot_deactivate_self(client, admin_headers):
    resp = client.delete("/api/users/1", headers=admin_headers)
    assert resp.status_code == 400