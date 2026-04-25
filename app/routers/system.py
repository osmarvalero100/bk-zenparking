from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.database import get_db
from app.models.models import User
from app.services.notifications import check_capacity_alert, get_parking_map

router = APIRouter(prefix="/system", tags=["System"])


@router.get("/capacity-alert")
async def get_capacity_alert(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return check_capacity_alert(db)


@router.get("/parking-map")
async def get_parking_map_endpoint(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    return {"zones": get_parking_map(db)}
