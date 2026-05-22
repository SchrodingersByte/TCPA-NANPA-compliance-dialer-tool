from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI

from app.core.config import settings
from app.database.connection import init_db
from app.routers.dial_check import router as compliance_router
from app.services.compliance_engine import dnc_cache_size, load_dnc_cache


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    await load_dnc_cache()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.include_router(compliance_router)


@app.get("/health", tags=["meta"])
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "dnc_cache_entries": str(dnc_cache_size()),
    }
