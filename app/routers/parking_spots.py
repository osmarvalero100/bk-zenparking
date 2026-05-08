from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import log_action

from app.core.auth import get_current_user, require_role, require_admin
from app.db.database import get_db
from app.models.models import User, UserRole, ParkingSpot, SpotStatus, VehicleType
from app.schemas.schemas import (
    ParkingSpotCreate,
    ParkingSpotUpdate,
    ParkingSpotOut,
    ParkingSpotDetailOut,
    MessageOut,
)

router = APIRouter(prefix="/spots", tags=["Parking Spots"])


@router.get("/", response_model=list[ParkingSpotOut])
async def get_spots(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    status: SpotStatus = None,
    vehicle_type: VehicleType = None,
    zone: str = None,
):
    query = db.query(ParkingSpot)

    if status:
        query = query.filter(ParkingSpot.status == status)
    if vehicle_type:
        query = query.filter(ParkingSpot.vehicle_type == vehicle_type)
    if zone:
        query = query.filter(ParkingSpot.zone == zone)

    return query.offset(skip).limit(limit).all()


@router.get("/available", response_model=list[ParkingSpotOut])
async def get_available_spots(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    vehicle_type: VehicleType = None,
):
    query = db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.FREE)

    if vehicle_type:
        query = query.filter(ParkingSpot.vehicle_type == vehicle_type)

    return query.all()


@router.get("/zones", response_model=list[str])
async def get_zones(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    zones = db.query(ParkingSpot.zone).distinct().all()
    return [z[0] for z in zones if z[0]]


@router.get("/statistics", response_model=dict)
async def get_spots_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    total = db.query(ParkingSpot).count()
    free = db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.FREE).count()
    occupied = (
        db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.OCCUPIED).count()
    )
    reserved = (
        db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.RESERVED).count()
    )
    maintenance = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.status == SpotStatus.MAINTENANCE)
        .count()
    )

    return {
        "total": total,
        "free": free,
        "occupied": occupied,
        "reserved": reserved,
        "maintenance": maintenance,
    }


@router.get("/{spot_id}", response_model=ParkingSpotOut)
async def get_spot(
    spot_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
        )
    return spot


@router.post("/", response_model=ParkingSpotOut, status_code=status.HTTP_201_CREATED)
async def create_spot(
    spot_data: ParkingSpotCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    existing = (
        db.query(ParkingSpot)
        .filter(ParkingSpot.spot_number == spot_data.spot_number)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Spot number already exists"
        )

    spot = ParkingSpot(
        spot_number=spot_data.spot_number,
        vehicle_type=spot_data.vehicle_type,
        zone=spot_data.zone,
        floor=spot_data.floor,
        row=spot_data.row,
        column=spot_data.column,
        is_near_exit=spot_data.is_near_exit,
    )

    db.add(spot)
    db.commit()
    db.refresh(spot)

    log_action(
        db,
        user=current_user,
        action="crear",
        resource="celda",
        resource_id=spot.id,
        details=f"Se creó la celda '{spot.spot_number}' zona {spot.zone} para {spot.vehicle_type.value}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return spot


@router.patch("/{spot_id}", response_model=ParkingSpotOut)
async def update_spot(
    spot_id: int,
    spot_data: ParkingSpotUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
        )

    if spot_data.vehicle_type:
        spot.vehicle_type = spot_data.vehicle_type
    if spot_data.status:
        spot.status = spot_data.status
    if spot_data.zone:
        spot.zone = spot_data.zone
    if spot_data.row:
        spot.row = spot_data.row
    if spot_data.column is not None:
        spot.column = spot_data.column
    if spot_data.is_near_exit is not None:
        spot.is_near_exit = spot_data.is_near_exit

    db.commit()
    db.refresh(spot)

    log_action(
        db,
        user=current_user,
        action="actualizar",
        resource="celda",
        resource_id=spot.id,
        details=f"Se actualizó la celda '{spot.spot_number}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return spot


@router.post("/{spot_id}/maintenance", response_model=MessageOut)
async def set_spot_maintenance(
    spot_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
        )

    spot.status = SpotStatus.MAINTENANCE
    db.commit()

    log_action(
        db,
        user=current_user,
        action="mantenimiento",
        resource="celda",
        resource_id=spot.id,
        details=f"Celda '{spot.spot_number}' puesta en mantenimiento",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Spot set to maintenance")


@router.post("/{spot_id}/release", response_model=MessageOut)
async def release_spot(
    spot_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
        )

    spot.status = SpotStatus.FREE
    db.commit()

    log_action(
        db,
        user=current_user,
        action="liberar",
        resource="celda",
        resource_id=spot.id,
        details=f"Celda '{spot.spot_number}' liberada",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Spot released successfully")


@router.delete("/{spot_id}", response_model=MessageOut)
async def delete_spot(
    spot_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    spot = db.query(ParkingSpot).filter(ParkingSpot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
        )

    db.delete(spot)
    db.commit()

    log_action(
        db,
        user=current_user,
        action="eliminar",
        resource="celda",
        resource_id=spot.id,
        details=f"Se eliminó la celda '{spot.spot_number}'",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Spot deleted successfully")
