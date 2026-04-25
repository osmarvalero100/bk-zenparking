from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import ParkingSpot, SpotStatus


def check_capacity_alert(db: Session) -> dict:
    total = db.query(ParkingSpot).count()
    if total == 0:
        return {"is_full": False, "capacity_percentage": 0, "alert": False}

    occupied = (
        db.query(ParkingSpot).filter(ParkingSpot.status == SpotStatus.OCCUPIED).count()
    )

    percentage = (occupied / total) * 100

    return {
        "is_full": occupied >= total,
        "capacity_percentage": round(percentage, 1),
        "total_spots": total,
        "occupied_spots": occupied,
        "available_spots": total - occupied,
        "alert": percentage >= 100,
        "alert_message": "PARKING FULL - 100% Capacity" if percentage >= 100 else None,
    }


def get_parking_map(db: Session) -> list[dict]:
    spots = db.query(ParkingSpot).all()

    parking_map = []
    for spot in spots:
        parking_map.append(
            {
                "id": spot.id,
                "spot_number": spot.spot_number,
                "vehicle_type": spot.vehicle_type.value,
                "status": spot.status.value,
                "zone": spot.zone,
                "floor": spot.floor,
                "row": spot.row,
                "column": spot.column,
                "is_near_exit": spot.is_near_exit,
            }
        )

    return parking_map
