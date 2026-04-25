"""Alembic seed script for initial data"""

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.database import Base
from app.models.models import (
    User,
    Role,
    Permission,
    Rate,
    VehicleType,
    ParkingSpot,
    SpotStatus,
    UserRole,
)
from app.core.auth import get_password_hash


def seed_data():
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        admin = User(
            username="admin",
            email="admin@zenparking.com",
            full_name="Administrator",
            role=UserRole.ADMIN,
            password_hash=get_password_hash("Admin123!"),
        )
        session.add(admin)

        operator = User(
            username="guardia1",
            email="guardia1@zenparking.com",
            full_name="Guardia Principal",
            role=UserRole.OPERATOR,
            password_hash=get_password_hash("Guardia123!"),
        )
        session.add(operator)

        auditor = User(
            username="auditor",
            email="auditor@zenparking.com",
            full_name="Auditor",
            role=UserRole.AUDITOR,
            password_hash=get_password_hash("Auditor123!"),
        )
        session.add(auditor)

        rates = [
            Rate(
                name="Tarifa Carro Hora",
                vehicle_type=VehicleType.CAR,
                rate_type="hourly",
                price_per_minute=150,
                free_minutes=5,
            ),
            Rate(
                name="Tarifa Moto Hora",
                vehicle_type=VehicleType.MOTORCYCLE,
                rate_type="hourly",
                price_per_minute=100,
                free_minutes=5,
            ),
            Rate(
                name="Tarifa Bicicleta Hora",
                vehicle_type=VehicleType.BICYCLE,
                rate_type="hourly",
                price_per_minute=50,
                free_minutes=5,
            ),
            Rate(
                name="Tarifa Discapacitado",
                vehicle_type=VehicleType.DISABLED,
                rate_type="hourly",
                price_per_minute=0,
                free_minutes=0,
            ),
        ]
        for rate in rates:
            session.add(rate)

        spots_config = [
            ("A1", VehicleType.CAR, "A", 1, "1", 1, True),
            ("A2", VehicleType.CAR, "A", 1, "1", 2, True),
            ("A3", VehicleType.CAR, "A", 1, "1", 3, False),
            ("A4", VehicleType.CAR, "A", 1, "2", 1, False),
            ("B1", VehicleType.CAR, "B", 1, "1", 1, True),
            ("B2", VehicleType.CAR, "B", 1, "1", 2, True),
            ("M1", VehicleType.MOTORCYCLE, "A", 1, "1", 1, True),
            ("M2", VehicleType.MOTORCYCLE, "A", 1, "1", 2, True),
            ("M3", VehicleType.MOTORCYCLE, "B", 1, "1", 1, False),
            ("D1", VehicleType.DISABLED, "A", 1, "1", 1, True),
        ]

        for spot_num, vtype, zone, floor, row, col, near_exit in spots_config:
            spot = ParkingSpot(
                spot_number=spot_num,
                vehicle_type=vtype,
                zone=zone,
                floor=floor,
                row=row,
                column=col,
                is_near_exit=near_exit,
                status=SpotStatus.FREE,
            )
            session.add(spot)

        session.commit()
        print(" Seed data created successfully!")

    except Exception as e:
        session.rollback()
        print(f"Error seeding data: {e}")
    finally:
        session.close()


if context.is_offline_mode():
    seed_data()
