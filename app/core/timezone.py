from zoneinfo import ZoneInfo
from datetime import datetime

from app.core.config import settings


def now() -> datetime:
    return datetime.now(ZoneInfo(settings.TIMEZONE))


def utcnow() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


def get_timezone() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def localize(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=ZoneInfo(settings.TIMEZONE))
