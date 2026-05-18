from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.core.constants import (
    COLLECTION_ACCOUNTS,
    COLLECTION_DRIVE_PENDING_FILES,
    COLLECTION_DRIVE_SYNC_STATE,
    COLLECTION_POSTS,
    COLLECTION_STANDBY_PROXIES,
    COLLECTION_UPLOAD_JOBS,
)
from app.core.exceptions import DatabaseError
from app.core.logger import get_logger

logger = get_logger(__name__)

_mongo_client: AsyncIOMotorClient | None = None
_redis_client: Redis | None = None


def get_mongo_client() -> AsyncIOMotorClient:
    if _mongo_client is None:
        raise DatabaseError("MongoDB client is not connected. Call connect_databases() first.")
    return _mongo_client


def get_database() -> AsyncIOMotorDatabase:
    settings = get_settings()
    return get_mongo_client()[settings.mongodb_db_name]


def get_redis() -> Redis:
    if _redis_client is None:
        raise DatabaseError("Redis client is not connected. Call connect_databases() first.")
    return _redis_client


async def connect_databases(settings: Settings | None = None) -> None:
    global _mongo_client, _redis_client

    cfg = settings or get_settings()

    _mongo_client = AsyncIOMotorClient(cfg.mongodb_uri)
    _redis_client = Redis.from_url(cfg.redis_url, decode_responses=True)

    await _mongo_client.admin.command("ping")
    await _redis_client.ping()

    await ensure_indexes(get_database())
    cfg.ensure_storage_dir()

    logger.info(
        "databases_connected",
        mongodb_db=cfg.mongodb_db_name,
        redis_url=cfg.redis_url.split("@")[-1],
    )


async def disconnect_databases() -> None:
    global _mongo_client, _redis_client

    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None

    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None

    logger.info("databases_disconnected")


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Ensure application indexes exist (idempotent)."""
    index_specs: list[tuple[Any, dict[str, Any]]] = [
        (
            db[COLLECTION_UPLOAD_JOBS].create_index,
            {
                "keys": [("post_id", 1), ("account_id", 1)],
                "unique": True,
                "name": "upload_jobs_post_account_unique",
            },
        ),
        (
            db[COLLECTION_UPLOAD_JOBS].create_index,
            {
                "keys": [("status", 1), ("retry_count", 1)],
                "name": "upload_jobs_status_retry",
            },
        ),
        (
            db[COLLECTION_UPLOAD_JOBS].create_index,
            {
                "keys": [("timing.completed_at", 1)],
                "expireAfterSeconds": 5_184_000,
                "name": "upload_jobs_completed_ttl",
            },
        ),
        (
            db[COLLECTION_ACCOUNTS].create_index,
            {"keys": [("status", 1)], "name": "accounts_status"},
        ),
        (
            db[COLLECTION_ACCOUNTS].create_index,
            {"keys": [("cooldown_until", 1)], "name": "accounts_cooldown"},
        ),
        (
            db[COLLECTION_POSTS].create_index,
            {"keys": [("status", 1)], "name": "posts_status"},
        ),
        (
            db[COLLECTION_POSTS].create_index,
            {
                "keys": [("drive.file_id", 1)],
                "unique": True,
                "sparse": True,
                "name": "posts_drive_file_unique",
            },
        ),
        (
            db[COLLECTION_DRIVE_PENDING_FILES].create_index,
            {"keys": [("file_id", 1)], "unique": True, "name": "drive_pending_file_unique"},
        ),
        (
            db[COLLECTION_DRIVE_PENDING_FILES].create_index,
            {
                "keys": [("first_seen_at", 1)],
                "expireAfterSeconds": 86_400,
                "name": "drive_pending_files_ttl",
            },
        ),
        (
            db[COLLECTION_STANDBY_PROXIES].create_index,
            {"keys": [("status", 1)], "name": "standby_proxies_status"},
        ),
        (
            db[COLLECTION_STANDBY_PROXIES].create_index,
            {"keys": [("created_at", 1)], "name": "standby_proxies_created_at"},
        ),
    ]

    for create_index, kwargs in index_specs:
        keys = kwargs.pop("keys")
        await create_index(keys, **kwargs)

    logger.info("database_indexes_ensured")


async def check_database_health() -> dict[str, str]:
    try:
        client = get_mongo_client()
        await client.admin.command("ping")
        redis = get_redis()
        pong = await redis.ping()
        return {
            "mongodb": "ok",
            "redis": "ok" if pong else "degraded",
        }
    except Exception as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {"mongodb": "error", "redis": "error", "detail": str(exc)}
