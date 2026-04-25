from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.auth import get_current_user, require_role, require_admin
from app.db.database import get_db
from app.models.models import User, UserRole, Vehicle, Blacklist
from app.schemas.schemas import (
    VehicleCreate,
    VehicleUpdate,
    VehicleOut,
    MessageOut,
)

router = APIRouter(prefix="/vehicles", tags=["Vehicles"])


@router.get("/", response_model=list[VehicleOut])
async def get_vehicles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    is_resident: bool = None,
    is_active: bool = None,
):
    query = db.query(Vehicle)

    if is_resident is not None:
        query = query.filter(Vehicle.is_resident == is_resident)
    if is_active is not None:
        query = query.filter(Vehicle.is_active == is_active)

    return query.offset(skip).limit(limit).all()


@router.get("/resident", response_model=list[VehicleOut])
async def get_resident_vehicles(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return db.query(Vehicle).filter(Vehicle.is_resident == True).all()


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(
    vehicle_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    return vehicle


@router.get("/plate/{plate}", response_model=VehicleOut)
async def get_vehicle_by_plate(
    plate: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )
    return vehicle


@router.post("/", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_data: VehicleCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    existing = (
        db.query(Vehicle).filter(Vehicle.plate == vehicle_data.plate.upper()).first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle with this plate already exists",
        )

    vehicle = Vehicle(
        plate=vehicle_data.plate.upper(),
        vehicle_type=vehicle_data.vehicle_type,
        owner_name=vehicle_data.owner_name,
        owner_phone=vehicle_data.owner_phone,
        owner_email=vehicle_data.owner_email,
        is_resident=vehicle_data.is_resident,
        monthly_rate_id=vehicle_data.monthly_rate_id,
    )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: int,
    vehicle_data: VehicleUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    if vehicle_data.owner_name:
        vehicle.owner_name = vehicle_data.owner_name
    if vehicle_data.owner_phone:
        vehicle.owner_phone = vehicle_data.owner_phone
    if vehicle_data.owner_email:
        vehicle.owner_email = vehicle_data.owner_email
    if vehicle_data.is_resident is not None:
        vehicle.is_resident = vehicle_data.is_resident
    if vehicle_data.is_active is not None:
        vehicle.is_active = vehicle_data.is_active
    if vehicle_data.monthly_rate_id is not None:
        vehicle.monthly_rate_id = vehicle_data.monthly_rate_id

    db.commit()
    db.refresh(vehicle)

    return vehicle


@router.delete("/{vehicle_id}", response_model=MessageOut)
async def delete_vehicle(
    vehicle_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    vehicle.is_active = False
    db.commit()

    return MessageOut(detail="Vehicle deactivated successfully")


@router.get("/blacklist/check/{plate}", response_model=dict)
async def check_blacklist(
    plate: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first()

    if not vehicle:
        return {"is_blacklisted": False, "details": None}

    blacklist = (
        db.query(Blacklist)
        .filter(Blacklist.vehicle_id == vehicle.id, Blacklist.is_active == True)
        .first()
    )

    if blacklist:
        return {
            "is_blacklisted": True,
            "reason": blacklist.reason,
            "alert_level": blacklist.alert_level,
        }

    return {"is_blacklisted": False, "details": None}
