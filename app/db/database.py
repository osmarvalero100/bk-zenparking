from zoneinfo import ZoneInfo
from datetime import datetime

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, echo=settings.DEBUG
)


@event.listens_for(engine, "connect")
def set_mysql_timezone(dbapi_connection, connection_record):
    tz = ZoneInfo(settings.TIMEZONE)
    offset = tz.utcoffset(datetime.now(tz))
    hours = int(offset.total_seconds() / 3600)
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET time_zone = '{hours:+03d}:00'")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
