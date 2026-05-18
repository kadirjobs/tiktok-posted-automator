from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants import COLLECTION_STANDBY_PROXIES, ProxyStatus
from app.core.security import encrypt_value
from app.models.proxy import StandbyProxy


class ProxyRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[COLLECTION_STANDBY_PROXIES]

    async def add_standby(self, proxy: StandbyProxy) -> str:
        now = datetime.now(UTC)
        payload = proxy.model_dump(mode="json", exclude_none=True)
        if proxy.password:
            payload["password"] = encrypt_value(proxy.password)
        payload["created_at"] = now
        result = await self._collection.insert_one(payload)
        return str(result.inserted_id)

    async def list_standby(self, status: ProxyStatus | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if status:
            query["status"] = status.value
        cursor = self._collection.find(query).sort("created_at", 1)
        return await cursor.to_list(length=100)

    async def get_by_id(self, proxy_id: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"_id": ObjectId(proxy_id)})

    async def pop_active_standby(self) -> dict[str, Any] | None:
        return await self._collection.find_one_and_update(
            {"status": ProxyStatus.ACTIVE.value},
            {"$set": {"status": ProxyStatus.DEAD.value}},
            sort=[("created_at", 1)],
        )

    async def update_status(self, proxy_id: str, status: ProxyStatus) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(proxy_id)},
            {"$set": {"status": status.value, "last_check_at": datetime.now(UTC)}},
        )

    async def count_by_status(self, status: ProxyStatus) -> int:
        return await self._collection.count_documents({"status": status.value})
