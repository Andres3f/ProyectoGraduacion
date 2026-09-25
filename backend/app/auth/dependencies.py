from typing import List

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.jwt import decode_access_token
from app.models.user import User, RoleEnum

# Esquema OAuth2 que extrae el token Bearer del header de autorización
# (el login emite el token en "/api/auth/login").
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extrae el usuario actual del token JWT."""
    # Excepción estándar de credenciales inválidas (401 con header de autenticación).
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    email: str | None = payload.get("sub")
    if email is None:
        raise credentials_exception

    # Resuelve el usuario por email declarado en el token y valida que esté activo.
    user = db.query(User).filter(User.email == email).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[RoleEnum]):
    """Fábrica de dependencias para verificar roles RBAC."""

    # Dependencia anidada: valida el rol del usuario ya autenticado por get_current_user.
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos suficientes para esta acción",
            )
        return current_user

    return role_checker
