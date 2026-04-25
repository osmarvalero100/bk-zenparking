from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Float,
    SmallInteger,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.database import Base
import enum


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    AUDITOR = "auditor"


class VehicleType(str, enum.Enum):
    CAR = "car"
    MOTORCYCLE = "motocycle"
    BICYCLE = "bicycle"
    DISABLED = "discapacitado"


class SpotStatus(str, enum.Enum):
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class FineType(str, enum.Enum):
    MAL_PARKING = "mal_parking"
    INVASION = "invasion"
    OVER_TIME = "over_time"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.OPERATOR)
    is_active = Column(Boolean, default=True)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    audit_logs = relationship(
        "AuditLog", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = relationship(
        "ParkingSession",
        back_populates="operator",
        foreign_keys="ParkingSession.operator_id",
    )


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    permissions = relationship(
        "Permission", back_populates="role", secondary="role_permissions"
    )


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    resource = Column(String(50), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    roles = relationship(
        "Role", back_populates="permissions", secondary="role_permissions"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(Integer, ForeignKey("roles.id"), primary_key=True)
    permission_id = Column(Integer, ForeignKey("permissions.id"), primary_key=True)


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(10), unique=True, nullable=False, index=True)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    owner_name = Column(String(100), nullable=False)
    owner_phone = Column(String(20), nullable=True)
    owner_email = Column(String(100), nullable=True)
    is_resident = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    monthly_rate_id = Column(Integer, ForeignKey("rates.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    monthly_rate = relationship("Rate", foreign_keys=[monthly_rate_id])
    sessions = relationship("ParkingSession", back_populates="vehicle")
    fines = relationship("Fine", back_populates="vehicle")
    blacklist = relationship("Blacklist", back_populates="vehicle", uselist=False)


class ParkingSpot(Base):
    __tablename__ = "parking_spots"

    id = Column(Integer, primary_key=True, index=True)
    spot_number = Column(String(10), unique=True, nullable=False, index=True)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    status = Column(Enum(SpotStatus), nullable=False, default=SpotStatus.FREE)
    zone = Column(String(20), nullable=True)
    floor = Column(SmallInteger, default=1)
    row = Column(String(5), nullable=True)
    column = Column(SmallInteger, nullable=True)
    is_near_exit = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sessions = relationship("ParkingSession", back_populates="spot")


class ParkingSession(Base):
    __tablename__ = "parking_sessions"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    spot_id = Column(Integer, ForeignKey("parking_spots.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticket_number = Column(String(20), unique=True, nullable=False, index=True)
    entry_time = Column(DateTime, server_default=func.now())
    exit_time = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    total_amount = Column(Float, default=0)
    payment_status = Column(String(20), default="pending")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="sessions")
    spot = relationship("ParkingSpot", back_populates="sessions")
    operator = relationship(
        "User", back_populates="sessions", foreign_keys=[operator_id]
    )


class Rate(Base):
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    vehicle_type = Column(Enum(VehicleType), nullable=False)
    rate_type = Column(String(20), nullable=False)
    price_per_minute = Column(Float, nullable=False)
    minimum_minutes = Column(Integer, default=0)
    maximum_minutes = Column(Integer, nullable=True)
    free_minutes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vehicles = relationship("Vehicle", back_populates="monthly_rate")


class Fine(Base):
    __tablename__ = "fines"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("parking_sessions.id"), nullable=True)
    fine_type = Column(Enum(FineType), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    photo_url = Column(String(255), nullable=True)
    status = Column(String(20), default="pending")
    paid_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="fines")
    creator = relationship("User", foreign_keys=[created_by])


class Blacklist(Base):
    __tablename__ = "blacklist"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), unique=True, nullable=False)
    reason = Column(Text, nullable=False)
    alert_level = Column(String(20), default="medium")
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vehicle = relationship("Vehicle", back_populates="blacklist")
    creator = relationship("User", foreign_keys=[created_by])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(50), nullable=False)
    resource_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="audit_logs")
