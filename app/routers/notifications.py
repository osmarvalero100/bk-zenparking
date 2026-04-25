from typing import Annotated
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_admin
from app.db.database import get_db
from app.models.models import User, Vehicle, ParkingSession
from app.services.email import send_notification, process_queue

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.post("/vehicle-entry/{session_id}")
async def notify_vehicle_entry(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
):
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
    if not vehicle or not vehicle.owner_email:
        raise HTTPException(status_code=400, detail="No owner email")

    message = f"""
    <h2>Entrada Registrada</h2>
    <p>Estimado cliente, su vehículo ha ingresado exitosamente al parqueadero.</p>
    <ul>
        <li><strong>Placa:</strong> {vehicle.plate}</li>
        <li><strong>Ticket:</strong> {session.ticket_number}</li>
        <li><strong>Hora de entrada:</strong> {session.entry_time}</li>
    </ul>
    <p>Gracias por preferirnos.</p>
    """

    send_notification(
        db=db,
        notification_type="vehicle_entry",
        recipient_email=vehicle.owner_email,
        recipient_phone=vehicle.owner_phone,
        subject="Entrada al Parqueadero - " + vehicle.plate,
        message=message,
    )

    return {"detail": "Notification queued"}


@router.post("/monthly-expiring")
async def notify_monthly_expiring(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    days_before: int = 5,
):
    from app.models.models import Rate

    residents = (
        db.query(Vehicle)
        .filter(Vehicle.is_resident == True, Vehicle.is_active == True)
        .all()
    )

    notified = 0
    for vehicle in residents:
        if not vehicle.owner_email:
            continue

        message = f"""
        <h2>Recordatorio de Vencimiento</h2>
        <p>Estimado cliente, su plan de mensualidad vencerá en {days_before} días.</li>
        <p>Por favor contactenos para renovar su suscripción.</p>
        <p>Placa: {vehicle.plate}</p>
        """

        send_notification(
            db=db,
            notification_type="monthly_expiring",
            recipient_email=vehicle.owner_email,
            recipient_phone=vehicle.owner_phone,
            subject="Recordatorio de mensualidad",
            message=message,
        )
        notified += 1

    return {"notified": notified}


@router.post("/time-exceeded/{session_id}")
async def notify_time_exceeded(
    session_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    session = db.query(ParkingSession).filter(ParkingSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
    if not vehicle or not vehicle.owner_email:
        raise HTTPException(status_code=400, detail="No owner email")

    message = f"""
    <h2>Tiempo Agotado</h2>
    <p>Señor usuario, su tiempo de gracia ha terminado. Por favor realizar el pago.</p>
    <ul>
        <li><strong>Placa:</strong> {vehicle.plate}</li>
        <li><strong>Ticket:</strong> {session.ticket_number}</li>
    </ul>
    """

    send_notification(
        db=db,
        notification_type="time_exceeded",
        recipient_email=vehicle.owner_email,
        recipient_phone=vehicle.owner_phone,
        subject="Tiempo Agotado - " + vehicle.plate,
        message=message,
    )

    return {"detail": "Notification queued"}


@router.post("/process-queue")
async def process_notification_queue(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
    limit: int = 10,
):
    result = process_queue(db, limit)
    return result


@router.get("/queue-status")
async def get_queue_status(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_admin)],
):
    from app.models.models import NotificationQueue

    pending = (
        db.query(NotificationQueue)
        .filter(NotificationQueue.status == "pending")
        .count()
    )

    sent = (
        db.query(NotificationQueue).filter(NotificationQueue.status == "sent").count()
    )

    failed = (
        db.query(NotificationQueue).filter(NotificationQueue.status == "failed").count()
    )

    return {"pending": pending, "sent": sent, "failed": failed}
