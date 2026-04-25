from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "ZenParking API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 3305
    DATABASE_USER: str = "root"
    DATABASE_PASSWORD: str = "r00t"
    DATABASE_NAME: str = "zen-parking"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@zenparking.com"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    MIN_PASSWORD_LENGTH: int = 8
    REQUIRES_UPPERCASE: bool = True
    REQUIRES_LOWERCASE: bool = True
    REQUIRES_NUMBERS: bool = True
    REQUIRES_SPECIAL: bool = True

    SESSION_TIMEOUT_MINUTES: int = 15
    MAX_LOGIN_ATTEMPTS: int = 5

    EMAIL_PROVIDER: str = "smtp"
    AWS_REGION: str = "us-east-1"
    AWS_SES_ACCESS_KEY: str = ""
    AWS_SES_SECRET_KEY: str = ""


settings = Settings()
