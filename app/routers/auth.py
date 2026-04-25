from datetime import datetime
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    get_current_user,
    validate_password_strength,
)
from app.core.config import settings
from app.db.database import get_db
from app.models.models import User, UserRole, AuditLog
from app.schemas.schemas import (
    UserCreate,
    UserOut,
    TokenOut,
    LoginRequest,
    MessageOut,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Annotated[Session, Depends(get_db)]):
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
        )

    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    is_valid, message = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Password weak: {message}"
        )

    password_hash = get_password_hash(user_data.password)

    user = User(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        role=user_data.role,
        password_hash=password_hash,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenOut)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.locked_until and user.locked_until > datetime.now():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is locked. Try again later.",
        )

    if not verify_password(form_data.password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now()
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.failed_attempts = 0
    user.locked_until = None
    user.last_login = datetime.now()
    db.commit()

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageOut)
async def logout(current_user: Annotated[User, Depends(get_current_user)]):
    return MessageOut(detail="Logged out successfully")


@router.post("/refresh", response_model=TokenOut)
async def refresh_token(current_user: Annotated[User, Depends(get_current_user)]):
    access_token = create_access_token(data={"sub": current_user.id})
    refresh_token = create_refresh_token(data={"sub": current_user.id})
    return TokenOut(access_token=access_token, refresh_token=refresh_token)


@router.post("/request-password-reset", response_model=MessageOut)
async def request_password_reset(email: str, db: Annotated[Session, Depends(get_db)]):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return MessageOut(detail="If email exists, reset instructions sent")

    reset_token = create_reset_token(data={"sub": user.id, "email": user.email})

    return MessageOut(
        detail=f"Password reset token: {reset_token[:20]}... (in production, email would be sent)"
    )


@router.post("/reset-password", response_model=MessageOut)
async def reset_password(
    token: str, new_password: str, db: Annotated[Session, Depends(get_db)]
):
    payload = decode_token(token)
    if payload.get("type") != "reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token"
        )

    is_valid, message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Weak password: {message}"
        )

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.password_hash = get_password_hash(new_password)
    db.commit()

    return MessageOut(detail="Password reset successfully")
