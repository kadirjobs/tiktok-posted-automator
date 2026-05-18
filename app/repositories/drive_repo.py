from datetime import UTC, datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants import (
    COLLECTION_DRIVE_PENDING_FILES,
    COLLECTION_DRIVE_SYNC_STATE,
    DRIVE_SYNC_STATE_ID,
)
from app.models.drive import DrivePendingFile, DriveSyncState


class DriveRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._sync = db[COLLECTION_DRIVE_SYNC_STATE]
        self._pending = db[COLLECTION_DRIVE_PENDING_FILES]

    async def get_sync_state(self) -> DriveSyncState:
        doc = await self._sync.find_one({"_id": DRIVE_SYNC_STATE_ID})
        if not doc:
            return DriveSyncState()
        return DriveSyncState.model_validate(doc)

    async def save_change_token(self, token: str) -> None:
        now = datetime.now(UTC)
        await self._sync.update_one(
            {"_id": DRIVE_SYNC_STATE_ID},
            {
                "$set": {
                    "last_change_token": token,
                    "updated_at": now,
                }
            },
            upsert=True,
        )

    async def get_pending_file(self, file_id: str) -> DrivePendingFile | None:
        doc = await self._pending.find_one({"file_id": file_id})
        if not doc:
            return None
        return DrivePendingFile.model_validate(doc)

    async def upsert_pending_file(self, pending: DrivePendingFile) -> None:
        payload = pending.model_dump(exclude_none=True)
        file_id = payload.pop("file_id")
        await self._pending.update_one(
            {"file_id": file_id},
            {"$set": payload},
            upsert=True,
        )

    async def delete_pending_file(self, file_id: str) -> None:
        await self._pending.delete_one({"file_id": file_id})

    async def list_ready_pending_files(self, min_stable_cycles: int) -> list[DrivePendingFile]:
        cursor = self._pending.find({"stable_cycles": {"$gte": min_stable_cycles}})
        docs: list[dict[str, Any]] = await cursor.to_list(length=500)
        return [DrivePendingFile.model_validate(doc) for doc in docs]

    async def find_pending_by_base_name(self, base_name: str) -> list[DrivePendingFile]:
        cursor = self._pending.find({"base_name": base_name})
        docs: list[dict[str, Any]] = await cursor.to_list(length=20)
        return [DrivePendingFile.model_validate(doc) for doc in docs]
