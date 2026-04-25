from fastapi import APIRouter

from app.routers import (
    auth,
    users,
    vehicles,
    parking_spots,
    sessions,
    rates,
    fines,
    blacklist,
    reports,
    system,
)

api_router = APIRouter(prefix="/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(vehicles.router)
api_router.include_router(parking_spots.router)
api_router.include_router(sessions.router)
api_router.include_router(rates.router)
api_router.include_router(fines.router)
api_router.include_router(blacklist.router)
api_router.include_router(reports.router)
api_router.include_router(system.router)
