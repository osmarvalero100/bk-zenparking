from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import User, Blacklist, Vehicle
from app.schemas.schemas import (
    BlacklistCreate,
    BlacklistUpdate,
    BlacklistOut,
    BlacklistDetailOut,
    MessageOut,
)

router = APIRouter(prefix="/blacklist", tags=["Blacklist"])


@router.get("/", response_model=list[BlacklistOut])
async def get_blacklist(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    is_active: bool = None,
):
    query = db.query(Blacklist)

    if is_active is not None:
        query = query.filter(Blacklist.is_active == is_active)

    return query.order_by(Blacklist.created_at.desc()).all()


@router.get("/{blacklist_id}", response_model=BlacklistOut)
async def get_blacklist_entry(
    blacklist_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    blacklist = db.query(Blacklist).filter(Blacklist.id == blacklist_id).first()
    if not blacklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found"
        )
    return blacklist


@router.post("/", response_model=BlacklistOut, status_code=status.HTTP_201_CREATED)
async def add_to_blacklist(
    blacklist_data: BlacklistCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = (
        db.query(Vehicle).filter(Vehicle.plate == blacklist_data.plate.upper()).first()
    )

    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    existing = db.query(Blacklist).filter(Blacklist.vehicle_id == vehicle.id).first()
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vehicle is already in blacklist",
            )
        existing.is_active = True
        existing.reason = blacklist_data.reason
        existing.alert_level = blacklist_data.alert_level
        existing.created_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    blacklist = Blacklist(
        vehicle_id=vehicle.id,
        reason=blacklist_data.reason,
        alert_level=blacklist_data.alert_level,
        created_by=current_user.id,
    )

    db.add(blacklist)
    db.commit()
    db.refresh(blacklist)

    return blacklist


@router.patch("/{blacklist_id}", response_model=BlacklistOut)
async def update_blacklist(
    blacklist_id: int,
    blacklist_data: BlacklistUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    blacklist = db.query(Blacklist).filter(Blacklist.id == blacklist_id).first()
    if not blacklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found"
        )

    if blacklist_data.reason:
        blacklist.reason = blacklist_data.reason
    if blacklist_data.alert_level:
        blacklist.alert_level = blacklist_data.alert_level
    if blacklist_data.is_active is not None:
        blacklist.is_active = blacklist_data.is_active

    db.commit()
    db.refresh(blacklist)

    return blacklist


@router.delete("/{blacklist_id}", response_model=MessageOut)
async def remove_from_blacklist(
    blacklist_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    blacklist = db.query(Blacklist).filter(Blacklist.id == blacklist_id).first()
    if not blacklist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blacklist entry not found"
        )

    blacklist.is_active = False
    db.commit()

    return MessageOut(detail="Vehicle removed from blacklist")
