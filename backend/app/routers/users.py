from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.auth.passwords import hash_password
from app.database import get_db
from app.models.user import User, RoleEnum
from app.schemas.user import UserOut, UserUpdate, UserCreate

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)):
    """Perfil del usuario autenticado."""
    return current_user


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    """Crear un nuevo usuario (solo admin)."""
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
    from app.services.audit import log_action

    log_action(
        db, current_user.id, "crear_usuario",
        entidad="user", entidad_id=user.id,
        detalle={"email": user.email, "role": user.role.value},
    )
    db.commit()
    return user


@router.get("", response_model=List[UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin, RoleEnum.gerente])),
):
    """Listar todos los usuarios (solo admin y gerente)."""
    return db.query(User).all()


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Actualizar usuario (solo admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    for field, value in user_in.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role([RoleEnum.admin])),
):
    """Ver detalle de un usuario (solo admin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user


class UserStatusUpdate(BaseModel):
    is_active: bool


@router.patch("/{user_id}/status", response_model=UserOut)
def update_user_status(
    user_id: int,
    body: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    """Activa o desactiva un usuario (solo admin). Audita el cambio de estado."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="No puedes desactivar tu propio usuario"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.is_active == body.is_active:
        raise HTTPException(
            status_code=400,
            detail=f"El usuario ya está {'activo' if body.is_active else 'inactivo'}",
        )
    user.is_active = body.is_active
    db.commit()
    db.refresh(user)
    from app.services.audit import log_action

    log_action(
        db, current_user.id, "cambiar_estado_usuario",
        entidad="user", entidad_id=user.id,
        detalle={"activo": user.is_active},
    )
    db.commit()
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([RoleEnum.admin])),
):
    """Desactivar usuario (solo admin).

    Soft delete: en lugar de borrar la fila (lo que rompería las FK de
    ``orders.created_by`` y ``routes.driver_id``), se marca ``is_active=False``.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400, detail="No puedes desactivar tu propio usuario"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    user.is_active = False
    db.commit()
    db.refresh(user)
    from app.services.audit import log_action

    log_action(
        db, current_user.id, "cambiar_estado_usuario",
        entidad="user", entidad_id=user.id,
        detalle={"activo": user.is_active},
    )
    db.commit()
    return {"detail": "Usuario desactivado", "id": user.id}
