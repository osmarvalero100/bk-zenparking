from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from app.core.audit import log_action
from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import User, Rate, VehicleType
from app.schemas.schemas import (
    RateCreate,
    RateUpdate,
    RateOut,
    MessageOut,
)

router = APIRouter(prefix="/rates", tags=["Rates"])


@router.get("/", response_model=list[RateOut])
async def get_rates(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    vehicle_type: VehicleType = None,
    is_active: bool = None,
):
    query = db.query(Rate)

    if vehicle_type:
        query = query.filter(Rate.vehicle_type == vehicle_type)
    if is_active is not None:
        query = query.filter(Rate.is_active == is_active)

    return query.all()


@router.get("/{rate_id}", response_model=RateOut)
async def get_rate(
    rate_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found"
        )
    return rate


@router.post("/", response_model=RateOut, status_code=status.HTTP_201_CREATED)
async def create_rate(
    rate_data: RateCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    rate = Rate(
        name=rate_data.name,
        vehicle_type=rate_data.vehicle_type,
        rate_type=rate_data.rate_type,
        price_per_minute=rate_data.price_per_minute,
        minimum_minutes=rate_data.minimum_minutes,
        maximum_minutes=rate_data.maximum_minutes,
        free_minutes=rate_data.free_minutes,
        is_active=rate_data.is_active,
        valid_from=rate_data.valid_from,
        valid_until=rate_data.valid_until,
    )

    db.add(rate)
    db.commit()
    db.refresh(rate)

    log_action(
        db,
        user=current_user,
        action="crear",
        resource="tarifa",
        resource_id=rate.id,
        details=f"Se creó la tarifa '{rate.name}' para {rate.vehicle_type.value} a ${rate.price_per_minute}/min",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return rate


@router.patch("/{rate_id}", response_model=RateOut)
async def update_rate(
    rate_id: int,
    rate_data: RateUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found"
        )

    if rate_data.name:
        rate.name = rate_data.name
    if rate_data.price_per_minute is not None:
        rate.price_per_minute = rate_data.price_per_minute
    if rate_data.minimum_minutes is not None:
        rate.minimum_minutes = rate_data.minimum_minutes
    if rate_data.maximum_minutes is not None:
        rate.maximum_minutes = rate_data.maximum_minutes
    if rate_data.free_minutes is not None:
        rate.free_minutes = rate_data.free_minutes
    if rate_data.is_active is not None:
        rate.is_active = rate_data.is_active

    db.commit()
    db.refresh(rate)

    log_action(
        db,
        user=current_user,
        action="actualizar",
        resource="tarifa",
        resource_id=rate.id,
        details=f"Se actualizó la tarifa '{rate.name}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return rate


@router.delete("/{rate_id}", response_model=MessageOut)
async def delete_rate(
    rate_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Rate not found"
        )

    rate.is_active = False
    db.commit()

    log_action(
        db,
        user=current_user,
        action="desactivar",
        resource="tarifa",
        resource_id=rate.id,
        details=f"Se desactivó la tarifa '{rate.name}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Rate deactivated successfully")
