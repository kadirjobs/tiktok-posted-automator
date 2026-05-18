import asyncio
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.core.config import Settings, get_settings
from app.core.exceptions import DriveNotConfiguredError, DriveSyncError
from app.core.logger import get_logger

logger = get_logger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveArchiver:
    """Moves processed files to the Drive archive folder."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def _build_drive_service(self) -> Any:
        if not self._settings.drive_configured:
            raise DriveNotConfiguredError("Google Drive is not configured.")
        credentials = service_account.Credentials.from_service_account_file(
            self._settings.google_application_credentials,
            scopes=DRIVE_SCOPES,
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    async def archive_file(self, file_id: str) -> None:
        if not self._settings.drive_archive_folder_id:
            logger.warning("drive_archive_skipped", reason="archive_folder_not_configured")
            return

        await asyncio.to_thread(self._move_to_archive, file_id)

    def _move_to_archive(self, file_id: str) -> None:
        service = self._build_drive_service()
        try:
            file_meta = service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file_meta.get("parents", []))
            service.files().update(
                fileId=file_id,
                addParents=self._settings.drive_archive_folder_id,
                removeParents=previous_parents,
                supportsAllDrives=True,
                fields="id, parents",
            ).execute()
            logger.info("drive_file_archived", file_id=file_id)
        except Exception as exc:
            logger.error("drive_archive_failed", file_id=file_id, error=str(exc))
            raise DriveSyncError(f"Failed to archive Drive file {file_id}.") from exc
