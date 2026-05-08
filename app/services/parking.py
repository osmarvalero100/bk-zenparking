from sqlalchemy.orm import Session

from app.core.timezone import now as tz_now, localize
from app.models.models import Rate, ParkingSession, Vehicle
from app.schemas.schemas import VehicleType


def calculate_parking_fee(
    vehicle_type: VehicleType, duration_minutes: int, db: Session
) -> float:
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


def compute_session_totals(session: ParkingSession, db: Session) -> tuple[int, float]:
    end = session.exit_time if session.exit_time else tz_now()
    duration = int((end - localize(session.entry_time)).total_seconds() / 60)

    vehicle = db.query(Vehicle).filter(Vehicle.id == session.vehicle_id).first()
    if not vehicle or vehicle.is_resident:
        return duration, 0.0

    amount = calculate_parking_fee(vehicle.vehicle_type, duration, db)
    return duration, amount
