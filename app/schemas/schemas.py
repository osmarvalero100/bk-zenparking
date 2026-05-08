from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, computed_field
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.core.timezone import now as tz_now, localize


class UserRole(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    AUDITOR = "auditor"


class VehicleType(str, Enum):
    CAR = "car"
    MOTORCYCLE = "motocycle"
    BICYCLE = "bicycle"
    DISABLED = "discapacitado"


class SpotStatus(str, Enum):
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"


class FineType(str, Enum):
    MAL_PARKING = "mal_parking"
    INVASION = "invasion"
    OVER_TIME = "over_time"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole = UserRole.OPERATOR


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserDetailOut(UserOut):
    last_login: Optional[datetime]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class PasswordStrengthResponse(BaseModel):
    is_valid: bool
    message: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class VehicleBase(BaseModel):
    plate: str
    vehicle_type: VehicleType
    owner_name: str
    owner_phone: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    is_resident: bool = False


class VehicleCreate(VehicleBase):
    monthly_rate_id: Optional[int] = None


class VehicleUpdate(BaseModel):
    owner_name: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_email: Optional[EmailStr] = None
    is_resident: Optional[bool] = None
    is_active: Optional[bool] = None
    monthly_rate_id: Optional[int] = None


class VehicleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    plate: str
    vehicle_type: VehicleType
    owner_name: str
    owner_phone: Optional[str]
    owner_email: Optional[str]
    is_resident: bool
    is_active: bool
    created_at: datetime


class ParkingSpotBase(BaseModel):
    spot_number: str
    vehicle_type: VehicleType
    zone: Optional[str] = None
    floor: int = 1
    row: Optional[str] = None
    column: Optional[int] = None
    is_near_exit: bool = False


class ParkingSpotCreate(ParkingSpotBase):
    pass


class ParkingSpotUpdate(BaseModel):
    vehicle_type: Optional[VehicleType] = None
    status: Optional[SpotStatus] = None
    zone: Optional[str] = None
    row: Optional[str] = None
    column: Optional[int] = None
    is_near_exit: Optional[bool] = None


class ParkingSpotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    spot_number: str
    vehicle_type: VehicleType
    status: SpotStatus
    zone: Optional[str]
    floor: int
    row: Optional[str]
    column: Optional[int]
    is_near_exit: bool
    created_at: datetime


class ParkingSpotDetailOut(ParkingSpotOut):
    vehicle: Optional[VehicleOut] = None
    session: Optional["ParkingSessionOut"] = None


class ParkingSessionBase(BaseModel):
    vehicle_id: int
    spot_id: int


class ParkingSessionCreate(BaseModel):
    plate: str
    spot_id: Optional[int] = None


class ParkingSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    spot_id: int
    operator_id: Optional[int]
    ticket_number: str
    entry_time: datetime
    exit_time: Optional[datetime]
    total_amount: float
    payment_status: str

    @computed_field
    @property
    def duration_minutes(self) -> int:
        if self.exit_time:
            return int((self.exit_time - self.entry_time).total_seconds() / 60)
        return int((tz_now() - localize(self.entry_time)).total_seconds() / 60)


class ParkingSessionEnd(BaseModel):
    payment_status: str = "paid"
    notes: Optional[str] = None


class RateBase(BaseModel):
    name: str
    vehicle_type: VehicleType
    rate_type: str
    price_per_minute: float
    minimum_minutes: int = 0
    maximum_minutes: Optional[int] = None
    free_minutes: int = 0
    is_active: bool = True


class RateCreate(RateBase):
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class RateUpdate(BaseModel):
    name: Optional[str] = None
    price_per_minute: Optional[float] = None
    minimum_minutes: Optional[int] = None
    maximum_minutes: Optional[int] = None
    free_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class RateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    vehicle_type: VehicleType
    rate_type: str
    price_per_minute: float
    minimum_minutes: int
    maximum_minutes: Optional[int]
    free_minutes: int
    is_active: bool


class FineBase(BaseModel):
    vehicle_id: int
    fine_type: FineType
    amount: float
    description: Optional[str] = None


class FineCreate(FineBase):
    session_id: Optional[int] = None
    photo_url: Optional[str] = None


class FineUpdate(BaseModel):
    fine_type: Optional[FineType] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    photo_url: Optional[str] = None
    status: Optional[str] = None


class FineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    session_id: Optional[int]
    fine_type: FineType
    amount: float
    description: Optional[str]
    photo_url: Optional[str]
    status: str
    paid_at: Optional[datetime]
    created_at: datetime


class BlacklistCreate(BaseModel):
    plate: str
    reason: str
    alert_level: str = "medium"


class BlacklistUpdate(BaseModel):
    reason: Optional[str] = None
    alert_level: Optional[str] = None
    is_active: Optional[bool] = None


class BlacklistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vehicle_id: int
    reason: str
    alert_level: str
    is_active: bool
    created_at: datetime


class BlacklistDetailOut(BlacklistOut):
    vehicle: VehicleOut


class AuditLogFilter(BaseModel):
    user_id: Optional[int] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: Optional[int]
    action: str
    resource: str
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: datetime


class DashboardStats(BaseModel):
    total_spots: int
    available_spots: int
    occupied_spots: int
    total_vehicles: int
    active_sessions: int
    daily_revenue: float
    today_entries: int
    today_exits: int
    active_fines: int


class ParkingMapOut(BaseModel):
    zones: List[str]
    spots: List[ParkingSpotOut]
    active_sessions: List[ParkingSessionOut]


class MessageOut(BaseModel):
    detail: str


class ErrorOut(BaseModel):
    detail: str
    code: Optional[str] = None


VehicleOut.model_rebuild()
ParkingSessionOut.model_rebuild()
