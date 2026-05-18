from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants import COLLECTION_POSTS, PostStatus
from app.models.post import Post


class PostsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[COLLECTION_POSTS]

    async def find_by_drive_file_id(self, file_id: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"drive.file_id": file_id})

    async def create_from_drive(
        self,
        *,
        video_file_id: str,
        change_token: str,
        caption: str,
        video_path: str = "",
        caption_path: str = "",
    ) -> str:
        now = datetime.now(UTC)
        post = Post(
            drive={"file_id": video_file_id, "change_token": change_token},
            files={"video_path": video_path, "caption_path": caption_path},
            status=PostStatus.QUEUED,
            caption=caption,
            created_at=now,
        )
        result = await self._collection.insert_one(
            post.model_dump(mode="json", exclude_none=True)
        )
        return str(result.inserted_id)

    async def update_status(self, post_id: str, status: PostStatus) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(post_id)},
            {"$set": {"status": status.value}},
        )

    async def update_after_download(
        self,
        post_id: str,
        *,
        video_path: str,
        caption_path: str,
        caption: str,
        checksum_sha256: str,
        status: PostStatus,
    ) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(post_id)},
            {
                "$set": {
                    "files.video_path": video_path,
                    "files.caption_path": caption_path,
                    "files.checksum_sha256": checksum_sha256,
                    "caption": caption,
                    "status": status.value,
                }
            },
        )
