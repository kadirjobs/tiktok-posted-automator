from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from app.api.admin_routes import router as admin_router
from app.api.auth_routes import router as auth_router
from app.api.callback_routes import router as callback_router
from app.core.config import get_settings
from app.core.database import check_database_health, connect_databases, disconnect_databases
from app.core.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    settings.ensure_storage_dir()
    await connect_databases(settings)
    logger.info("application_started", env=settings.app_env, app=settings.app_name)
    yield
    await disconnect_databases()
    logger.info("application_stopped")


_settings = get_settings()

app = FastAPI(
    title="TikTok Posted Automator",
    version="0.2.0",
    description="Daemon-based TikTok content distribution system.",
    lifespan=lifespan,
)

app.add_middleware(SessionMiddleware, secret_key=_settings.secret_key)

app.include_router(auth_router)
app.include_router(callback_router)
app.include_router(admin_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, Any]:
    settings = get_settings()
    db_health = await check_database_health()
    return {
        "status": "ok" if db_health.get("mongodb") == "ok" else "degraded",
        "app": settings.app_name,
        "env": settings.app_env,
        "drive_configured": settings.drive_configured,
        "tiktok_configured": settings.tiktok_configured,
        "admin_configured": settings.admin_configured,
        "services": db_health,
    }


@app.get("/ready", tags=["health"])
async def ready() -> dict[str, str]:
    health = await check_database_health()
    if health.get("mongodb") != "ok" or health.get("redis") != "ok":
        return {"status": "not_ready"}
    return {"status": "ready"}
