"""Punto de entrada del backend FastAPI de ComunIA."""

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Motor type-safe de triaje de incidencias para administradores "
        "de comunidades de propietarios."
    ),
)

app.include_router(router, prefix="/api/v1", tags=["ComunIA"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }
