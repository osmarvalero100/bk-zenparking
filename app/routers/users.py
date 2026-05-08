from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi import Request
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin, get_password_hash
from app.core.audit import log_action
from app.db.database import get_db
from app.models.models import User, UserRole, AuditLog
from app.schemas.schemas import (
    UserCreate,
    UserUpdate,
    UserOut,
    UserDetailOut,
    PasswordChange,
    MessageOut,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=list[UserOut])
async def get_users(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
):
    return db.query(User).offset(skip).limit(limit).all()


@router.get("/me", response_model=UserDetailOut)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_user)],
):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        password_hash=get_password_hash(user_data.password),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    log_action(
        db,
        user=current_user,
        action="crear",
        resource="usuario",
        resource_id=user.id,
        details=f"Se creó el usuario '{user.username}' con rol {user.role.value}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_data.email and user_data.email != user.email:
        if db.query(User).filter(User.email == user_data.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
            )
        user.email = user_data.email

    if user_data.full_name:
        user.full_name = user_data.full_name
    if user_data.role:
        user.role = user_data.role
    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()
    db.refresh(user)

    log_action(
        db,
        user=current_user,
        action="actualizar",
        resource="usuario",
        resource_id=user.id,
        details=f"Se actualizó el usuario '{user.username}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return user


@router.delete("/{user_id}", response_model=MessageOut)
async def delete_user(
    user_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = False
    db.commit()

    log_action(
        db,
        user=current_user,
        action="desactivar",
        resource="usuario",
        resource_id=user.id,
        details=f"Se desactivó el usuario '{user.username}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="User deactivated successfully")


@router.post("/{user_id}/activate", response_model=MessageOut)
async def activate_user(
    user_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = True
    db.commit()

    log_action(
        db,
        user=current_user,
        action="activar",
        resource="usuario",
        resource_id=user.id,
        details=f"Se activó el usuario '{user.username}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="User activated successfully")


@router.post("/change-password", response_model=MessageOut)
async def change_password(
    password_data: PasswordChange,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    from app.core.auth import verify_password

    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(password_data.new_password)
    db.commit()

    log_action(
        db,
        user=current_user,
        action="cambiar_contraseña",
        resource="usuario",
        resource_id=current_user.id,
        details=f"Cambio de contraseña para '{current_user.username}'",
    )

    return MessageOut(detail="Password changed successfully")
