from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import DRIVE_SYNC_STATE_ID


class DriveSyncState(BaseModel):
    id: str = Field(default=DRIVE_SYNC_STATE_ID, alias="_id")
    last_change_token: str = ""
    updated_at: datetime | None = None

    model_config = {"populate_by_name": True}


class DrivePendingFile(BaseModel):
    file_id: str
    base_name: str
    is_video: bool = False
    mime_type: str = ""
    size: int = 0
    modified_time: str = ""
    stable_cycles: int = 0
    first_seen_at: datetime | None = None
    last_checked_at: datetime | None = None
    paired_caption_file_id: str | None = None
    paired_video_file_id: str | None = None
