from typing import Annotated, List
from datetime import datetime, timedelta
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import csv

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import User, ParkingSession, Vehicle, ParkingSpot, Fine, AuditLog
from app.schemas.schemas import (
    AuditLogFilter,
    AuditLogOut,
    MessageOut,
)

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/daily-movements")
async def get_daily_movements_report(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date: str = Query(default=None, description="Date in YYYY-MM-DD format"),
):
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
    else:
        target_date = datetime.now().date()

    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    sessions = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.entry_time >= start_datetime,
            ParkingSession.entry_time < end_datetime,
        )
        .all()
    )

    entries = []
    exits = []

    for session in sessions:
        vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
        spot = db.query(ParkingSpot).filter(ParkingSpot.id == session.spot_id).first()

        session_data = {
            "ticket": session.ticket_number,
            "plate": vehicle.plate if vehicle else "Unknown",
            "spot": spot.spot_number if spot else "Unknown",
            "entry": session.entry_time.isoformat() if session.entry_time else None,
            "exit": session.exit_time.isoformat() if session.exit_time else None,
            "duration": session.duration_minutes,
            "amount": session.total_amount,
            "payment_status": session.payment_status,
        }

        entries.append(session_data)

        if session.exit_time:
            exits.append(session_data)

    return {
        "date": target_date.isoformat(),
        "total_entries": len(entries),
        "total_exits": len(exits),
        "entries": entries,
        "exits": exits,
    }


@router.get("/daily-movements-csv")
async def get_daily_movements_csv(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    date: str = Query(default=None, description="Date in YYYY-MM-DD format"),
):
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD",
            )
    else:
        target_date = datetime.now().date()

    start_datetime = datetime.combine(target_date, datetime.min.time())
    end_datetime = start_datetime + timedelta(days=1)

    sessions = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.entry_time >= start_datetime,
            ParkingSession.entry_time < end_datetime,
        )
        .all()
    )

    output = BytesIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Ticket",
            "Plate",
            "Spot",
            "Entry Time",
            "Exit Time",
            "Duration (min)",
            "Amount",
            "Payment Status",
        ]
    )

    for session in sessions:
        vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
        spot = db.query(ParkingSpot).filter(ParkingSpot.id == session.spot_id).first()

        writer.writerow(
            [
                session.ticket_number,
                vehicle.plate if vehicle else "Unknown",
                spot.spot_number if spot else "Unknown",
                session.entry_time.isoformat() if session.entry_time else "",
                session.exit_time.isoformat() if session.exit_time else "",
                session.duration_minutes or "",
                session.total_amount or "",
                session.payment_status,
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=movements_{target_date}.csv"
        },
    )


@router.get("/audit-logs", response_model=List[AuditLogOut])
async def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    action: str = None,
    resource: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
):
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action.like(f"%{action}%"))
    if resource:
        query = query.filter(AuditLog.resource == resource)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)

    return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/revenue-summary")
async def get_revenue_summary(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: datetime = None,
    end_date: datetime = None,
):
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    from sqlalchemy import func

    total_revenue = (
        db.query(func.sum(ParkingSession.total_amount))
        .filter(
            ParkingSession.entry_time >= start_date,
            ParkingSession.entry_time <= end_date,
            ParkingSession.exit_time != None,
        )
        .scalar()
        or 0
    )

    sessions_count = (
        db.query(ParkingSession)
        .filter(
            ParkingSession.entry_time >= start_date,
            ParkingSession.entry_time <= end_date,
            ParkingSession.exit_time != None,
        )
        .count()
    )

    fines_total = (
        db.query(func.sum(Fine.amount))
        .filter(
            Fine.created_at >= start_date,
            Fine.created_at <= end_date,
            Fine.status == "paid",
        )
        .scalar()
        or 0
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "parking_revenue": float(total_revenue),
        "fines_revenue": float(fines_total),
        "total_revenue": float(total_revenue) + float(fines_total),
        "sessions_count": sessions_count,
    }


@router.get("/spots-utilization")
async def get_spots_utilization(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    start_date: datetime = None,
    end_date: datetime = None,
):
    if not start_date:
        start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if not end_date:
        end_date = datetime.now()

    from sqlalchemy import func

    spots = db.query(ParkingSpot).all()

    utilization = []
    for spot in spots:
        usage_count = (
            db.query(ParkingSession)
            .filter(
                ParkingSession.spot_id == spot.id,
                ParkingSession.entry_time >= start_date,
                ParkingSession.entry_time <= end_date,
            )
            .count()
        )

        utilization.append(
            {
                "spot_number": spot.spot_number,
                "zone": spot.zone,
                "vehicle_type": spot.vehicle_type.value,
                "total_sessions": usage_count,
            }
        )

    return sorted(utilization, key=lambda x: x["total_sessions"], reverse=True)
