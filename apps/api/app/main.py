import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router


def create_app() -> FastAPI:
    extra_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ]
    application = FastAPI(
        title="QALDY AI — Career Quest API",
        version="0.1.0",
        description="Explainable employee development recommendations.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *extra_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
