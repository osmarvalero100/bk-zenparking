from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import api_router
from app.db.database import engine, Base
from app.models.models import *


def check_and_run_migrations():
    """Check and run pending migrations on startup"""
    from sqlalchemy import inspect

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if not existing_tables or len(existing_tables) <= 1:
        print("No tables found, creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("Tables created successfully")

    tables = inspector.get_table_names()
    if "alembic_version" in tables:
        from alembic.config import Config
        from alembic import command

        try:
            cfg = Config("alembic.ini")
            command.upgrade(cfg, "head")
            print("Migrations run successfully")
        except Exception as e:
            print(f"Migration check: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    check_and_run_migrations()
    yield
    print("Shutting down application")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Welcome to ZenParking API", "version": settings.APP_VERSION}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
