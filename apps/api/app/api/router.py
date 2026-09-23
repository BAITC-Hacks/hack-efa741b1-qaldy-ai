from fastapi import APIRouter

from app.api import auth
from app.api.routes import employees, health, hr, imports

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(health.router)
api_router.include_router(employees.router)
api_router.include_router(hr.router)
api_router.include_router(imports.router)
