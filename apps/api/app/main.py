import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.dependencies import assert_backend_ready
from app.api.router import api_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Fail before accepting traffic when the immutable dataset or persistence
    # boundary is unavailable/misconfigured.
    assert_backend_ready()
    yield


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
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", *extra_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @application.middleware("http")
    async def prevent_sensitive_response_caching(
        request: Request,
        call_next,
    ) -> Response:
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            response.headers["Pragma"] = "no-cache"
        return response

    application.include_router(api_router)
    return application


app = create_app()
