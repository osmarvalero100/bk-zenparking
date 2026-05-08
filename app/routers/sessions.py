from typing import Annotated
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.auth import get_current_user
from app.core.timezone import now as tz_now, localize
from app.db.database import get_db
from app.models.models import (
    User,
    UserRole,
    Vehicle,
    ParkingSpot,
    ParkingSession,
    SpotStatus,
    Fine,
    Blacklist,
    AuditLog,
)
from app.schemas.schemas import (
    ParkingSessionCreate,
    ParkingSessionOut,
    ParkingSessionEnd,
    DashboardStats,
    VehicleType,
    FineType,
    MessageOut,
)
from app.core.config import settings
import random
import string

router = APIRouter(prefix="/sessions", tags=["Parking Sessions"])


def generate_ticket_number():
    return (
        f"TKT{tz_now().strftime('%Y%m%d')}{''.join(random.choices(string.digits, k=6))}"
    )


def calculate_parking_fee(
    vehicle_type: VehicleType, duration_minutes: int, db: Session
) -> float:
    from app.models.models import Rate

    rate = (
        db.query(Rate)
        .filter(Rate.vehicle_type == vehicle_type, Rate.is_active == True)
        .filter((Rate.valid_from == None) | (Rate.valid_from <= tz_now()))
        .filter((Rate.valid_until == None) | (Rate.valid_until >= tz_now()))
        .first()
    )

    if not rate:
        rate = db.query(Rate).filter(Rate.vehicle_type == vehicle_type).first()

    if not rate:
        default_rates = {
            VehicleType.CAR: 150,
            VehicleType.MOTORCYCLE: 100,
            VehicleType.BICYCLE: 50,
            VehicleType.DISABLED: 0,
        }
        return default_rates.get(vehicle_type, 150) * duration_minutes

    billable_minutes = max(0, duration_minutes - rate.free_minutes)
    if rate.maximum_minutes and duration_minutes > rate.maximum_minutes:
        billable_minutes = rate.maximum_minutes - rate.free_minutes

    return rate.price_per_minute * billable_minutes


@router.get("/", response_model=list[ParkingSessionOut])
async def get_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
):
    query = db.query(ParkingSession)

    if active_only:
        query = query.filter(ParkingSession.exit_time == None)

    return (
        query.order_by(ParkingSession.entry_time.desc()).offset(skip).limit(limit).all()
    )


@router.get("/active", response_model=list[ParkingSessionOut])
async def get_active_sessions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return db.query(ParkingSession).filter(ParkingSession.exit_time == None).all()


@router.get("/statistics", response_model=DashboardStats)
async def get_dashboard_statistics(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    today = tz_now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)

    total_spots = db.query(ParkingSpot).count()
    available_spots = (
        db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.FREE).count()
    )
    occupied_spots = (
        db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.OCCUPIED).count()
    )

    total_vehicles = db.query(Vehicle).filter(Vehicle.is_active == True).count()
    active_sessions = (
        db.query(ParkingSession).filter(ParkingSession.exit_time == None).count()
    )

    daily_revenue = (
        db.query(func.sum(ParkingSession.total_amount))
        .filter(ParkingSession.entry_time >= today, ParkingSession.exit_time != None)
        .scalar()
        or 0
    )

    today_entries = (
        db.query(ParkingSession).filter(ParkingSession.entry_time >= today).count()
    )

    today_exits = (
        db.query(ParkingSession)
        .filter(ParkingSession.exit_time >= today, ParkingSession.exit_time < tomorrow)
        .count()
    )

    active_fines = db.query(Fine).filter(Fine.status == "pending").count()

    return DashboardStats(
        total_spots=total_spots,
        available_spots=available_spots,
        occupied_spots=occupied_spots,
        total_vehicles=total_vehicles,
        active_sessions=active_sessions,
        daily_revenue=float(daily_revenue),
        today_entries=today_entries,
        today_exits=today_exits,
        active_fines=active_fines,
    )


@router.get("/search", response_model=ParkingSessionOut)
async def search_session(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    plate: str = None,
    ticket: str = None,
):
    """Search session by plate or ticket number"""
    if not plate and not ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide plate or ticket parameter",
        )

    session = None

    if ticket:
        session = (
            db.query(ParkingSession)
            .filter(ParkingSession.ticket_number == ticket)
            .first()
        )

    if not session and plate:
        vehicle = db.query(Vehicle).filter(Vehicle.plate == plate.upper()).first()
        if vehicle:
            session = (
                db.query(ParkingSession)
                .filter(
                    ParkingSession.vehicle_id == vehicle.id,
                    ParkingSession.exit_time == None,
                )
                .first()
            )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active session found",
        )

    # Calculate duration and total_amount if session is active
    if session.exit_time is None:
        now = tz_now()
        duration = int((now - localize(session.entry_time)).total_seconds() / 60)
        session.duration_minutes = duration

        vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
        if vehicle and vehicle.is_resident:
            session.total_amount = 0
        elif vehicle:
            session.total_amount = calculate_parking_fee(
                vehicle.vehicle_type, duration, db
            )
        else:
            session.total_amount = 0

    return session


@router.get("/{session_id}", response_model=ParkingSessionOut)
async def get_session(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.get("/ticket/{ticket_number}", response_model=ParkingSessionOut)
async def get_session_by_ticket(
    ticket_number: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    session = (
        db.query(ParkingSession)
        .filter(ParkingSession.ticket_number == ticket_number)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return session


@router.post(
    "/entry", response_model=ParkingSessionOut, status_code=status.HTTP_201_CREATED
)
async def vehicle_entry(
    session_data: ParkingSessionCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = (
        db.query(Vehicle).filter(Vehicle.plate == session_data.plate.upper()).first()
    )

    if not vehicle:
        vehicle = Vehicle(
            plate=session_data.plate.upper(),
            vehicle_type=VehicleType.CAR,
            owner_name="Visitante",
        )
        db.add(vehicle)
        db.commit()
        db.refresh(vehicle)

    blacklist = (
        db.query(Blacklist)
        .filter(Blacklist.vehicle_id == vehicle.id, Blacklist.is_active == True)
        .first()
    )
    if blacklist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Vehículo en lista negra: {blacklist.reason}",
        )

    active_session = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.vehicle_id == vehicle.id, ParkingSession.exit_time == None
        )
        .first()
    )
    if active_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vehicle already has an active session",
        )

    spot = None
    if session_data.spot_id:
        spot = (
            db.query(ParkingSpot).filter(ParkingSpot.id == session_data.spot_id).first()
        )
        if not spot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Spot not found"
            )
        if spot.status != SpotStatus.FREE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Spot is not available"
            )
    else:
        spot = (
            db.query(ParkingSpot)
            .filter(
                ParkingSpot.vehicle_type == vehicle.vehicle_type,
                ParkingSpot.status == SpotStatus.FREE,
            )
            .order_by(ParkingSpot.is_near_exit.desc())
            .first()
        )

        if not spot:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No hay celdas de parqueo disponibles para este tipo de vehículo",
            )

    spot.status = SpotStatus.OCCUPIED

    session = ParkingSession(
        vehicle_id=vehicle.id,
        spot_id=spot.id,
        operator_id=current_user.id,
        ticket_number=generate_ticket_number(),
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return session


@router.patch("/{session_id}/exit", response_model=ParkingSessionOut)
async def vehicle_exit(
    session_id: int,
    exit_data: ParkingSessionEnd,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    if session.exit_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle has already exited"
        )

    pending_fines = (
        db.query(Fine)
        .filter(Fine.vehicle_id == session.vehicle_id, Fine.status == "pending")
        .first()
    )
    if pending_fines:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El vehículo tiene multas pendientes. No puede salir.",
        )

    exit_time = tz_now()
    duration = int((exit_time - localize(session.entry_time)).total_seconds() / 60)

    vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()

    if vehicle.is_resident:
        total_amount = 0
    else:
        total_amount = calculate_parking_fee(vehicle.vehicle_type, duration, db)

    session.exit_time = exit_time
    session.duration_minutes = duration
    session.total_amount = total_amount
    session.payment_status = exit_data.payment_status
    session.notes = exit_data.notes

    spot = db.query(ParkingSpot).filter(ParkingSpot.id == session.spot_id).first()
    if spot:
        spot.status = SpotStatus.FREE

    db.commit()
    db.refresh(session)

    return session
