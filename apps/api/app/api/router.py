from fastapi import APIRouter

from app.api.routes import employees, health, hr

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(employees.router)
api_router.include_router(hr.router)
