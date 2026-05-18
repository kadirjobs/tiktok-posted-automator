from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from app.core.constants import REDIS_TOKEN_REFRESH_LOCK_PREFIX
from app.core.database import get_redis


@asynccontextmanager
async def redis_lock(key: str, ttl_seconds: int = 120) -> AsyncIterator[bool]:
    """
    Yield True if lock acquired, False otherwise.
    Lock is released on context exit when acquired.
    """
    redis = get_redis()
    acquired = await redis.set(key, "1", nx=True, ex=ttl_seconds)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await redis.delete(key)


def token_refresh_lock_key(account_id: str) -> str:
    return f"{REDIS_TOKEN_REFRESH_LOCK_PREFIX}{account_id}"
