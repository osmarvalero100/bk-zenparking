from typing import Annotated
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.audit import log_action

from app.core.auth import get_current_user, require_role
from app.core.timezone import now as tz_now
from app.db.database import get_db
from app.models.models import User, UserRole, Fine, FineType, Vehicle
from app.schemas.schemas import (
    FineCreate,
    FineOut,
    MessageOut,
)

router = APIRouter(prefix="/fines", tags=["Fines"])


@router.get("/", response_model=list[FineOut])
async def get_fines(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    skip: int = 0,
    limit: int = 100,
    status: str = None,
):
    query = db.query(Fine)

    if status:
        query = query.filter(Fine.status == status)

    return query.order_by(Fine.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{fine_id}", response_model=FineOut)
async def get_fine(
    fine_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    fine = db.query(Fine).filter(Fine.id == fine_id).first()
    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found"
        )
    return fine


@router.post("/", response_model=FineOut, status_code=status.HTTP_201_CREATED)
async def create_fine(
    fine_data: FineCreate,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == fine_data.vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found"
        )

    fine = Fine(
        vehicle_id=fine_data.vehicle_id,
        session_id=fine_data.session_id,
        fine_type=fine_data.fine_type,
        amount=fine_data.amount,
        description=fine_data.description,
        photo_url=fine_data.photo_url,
        created_by=current_user.id,
    )

    db.add(fine)
    db.commit()
    db.refresh(fine)

    log_action(
        db,
        user=current_user,
        action="crear",
        resource="multa",
        resource_id=fine.id,
        details=f"Se creó multa de ${fine.amount:.0f} al vehículo placa '{vehicle.plate}' - {fine.description}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return fine


@router.patch("/{fine_id}/pay", response_model=MessageOut)
async def pay_fine(
    fine_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    fine = db.query(Fine).filter(Fine.id == fine_id).first()
    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found"
        )

    if fine.status == "paid":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Fine is already paid"
        )

    fine.status = "paid"
    fine.paid_at = tz_now()
    db.commit()

    log_action(
        db,
        user=current_user,
        action="pagar",
        resource="multa",
        resource_id=fine.id,
        details=f"Multa pagada - ${fine.amount:.0f}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Fine paid successfully")


@router.delete("/{fine_id}", response_model=MessageOut)
async def delete_fine(
    fine_id: int,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
):
    fine = db.query(Fine).filter(Fine.id == fine_id).first()
    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fine not found"
        )

    db.delete(fine)
    db.commit()

    log_action(
        db,
        user=current_user,
        action="eliminar",
        resource="multa",
        resource_id=fine.id,
        details=f"Se eliminó la multa #{fine.id}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    return MessageOut(detail="Fine deleted successfully")
