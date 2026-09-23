from fastapi import APIRouter

from app.api.routes import demo, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(demo.router, prefix="/api/v1/demo", tags=["demo"])
