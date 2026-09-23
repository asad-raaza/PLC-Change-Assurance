"""FastAPI entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import router
from app.config import get_settings
from app.persistence.database import get_engine, get_session_factory
from app.persistence.orm import Base
from app.services.runtime import get_runtime

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    engine = get_engine()
    Base.metadata.create_all(engine)
    runtime = get_runtime()
    if settings.seed_on_startup:
        db = get_session_factory()()
        try:
            runtime.seed(db)
            db.commit()
        finally:
            db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Cyber-Physical PLC Change Assurance Gateway",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": __version__,
        "operating_mode": settings.operating_mode,
        "lab_mode": settings.lab_mode,
        "enforcement_enabled": settings.enforcement_enabled,
    }
