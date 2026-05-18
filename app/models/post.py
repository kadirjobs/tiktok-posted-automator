from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import PostStatus


class PostDriveInfo(BaseModel):
    file_id: str = ""
    change_token: str = ""


class PostFiles(BaseModel):
    video_path: str = ""
    caption_path: str = ""
    checksum_sha256: str = ""


class PostDistributionSummary(BaseModel):
    success_count: int = 0
    failed_count: int = 0
    pending_count: int = 0


class Post(BaseModel):
    drive: PostDriveInfo = Field(default_factory=PostDriveInfo)
    files: PostFiles = Field(default_factory=PostFiles)
    status: PostStatus = PostStatus.QUEUED
    caption: str = ""
    distribution_summary: PostDistributionSummary = Field(
        default_factory=PostDistributionSummary
    )
    created_at: datetime | None = None
    completed_at: datetime | None = None
