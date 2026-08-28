from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.schemas.token import Token, TokenPair, LoginRequest, RefreshRequest
from app.auth.passwords import hash_password, verify_password
from app.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


def _token_pair_for(user: User) -> TokenPair:
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email, "role": user.role.value}
    )
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/register", response_model=Token)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Registro de nuevo usuario."""
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado",
        )
    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=user_in.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return Token(access_token=token)


@router.post("/login", response_model=TokenPair)
def login(form: LoginRequest, db: Session = Depends(get_db)):
    """Inicio de sesión con email y contraseña. Devuelve access + refresh."""
    user = db.query(User).filter(User.email == form.email).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada",
        )
    return _token_pair_for(user)


@router.post("/refresh", response_model=TokenPair)
def refresh(form: RefreshRequest, db: Session = Depends(get_db)):
    """Intercambia un refresh token válido por un nuevo par de tokens."""
    payload = decode_refresh_token(form.refresh_token)
    if payload is None or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
        )
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no válido",
        )
    return _token_pair_for(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """Cierra la sesión del usuario.

    Decisión de diseño: los JWT son stateless, por lo que el servidor no
    conserva estado de sesión. Para revocar el acceso, el frontend debe
    descartar el access_token y el refresh_token almacenados (localStorage /
    memoria). Esto es suficiente para el alcance de la tesis; una solución
    blocklist (tabla `revoked_tokens`) quedaría documentada como trabajo futuro.
    """
    return None
