import asyncio
import hashlib
import io
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from app.core.config import Settings, get_settings
from app.core.exceptions import DriveNotConfiguredError, DriveSyncError
from app.core.logger import get_logger

logger = get_logger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]


class DriveDownloader:
    """Downloads stable media pairs from Google Drive to local storage."""

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

    def build_post_storage_dir(self, post_id: str) -> Path:
        target = self._settings.storage_path / post_id
        target.mkdir(parents=True, exist_ok=True)
        return target

    async def download_video(self, file_id: str, destination: Path) -> Path:
        return await asyncio.to_thread(self._download_binary, file_id, destination)

    async def download_caption(self, file_id: str, destination: Path) -> tuple[Path, str]:
        path = await asyncio.to_thread(self._download_binary, file_id, destination)
        caption = path.read_text(encoding="utf-8").strip()
        return path, caption

    async def sha256_file(self, path: Path) -> str:
        return await asyncio.to_thread(self._sha256_sync, path)

    def _download_binary(self, file_id: str, destination: Path) -> Path:
        service = self._build_drive_service()
        request = service.files().get_media(fileId=file_id)
        destination.parent.mkdir(parents=True, exist_ok=True)

        buffer = io.FileIO(str(destination), "wb")
        try:
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        except Exception as exc:
            logger.error("drive_download_failed", file_id=file_id, error=str(exc))
            raise DriveSyncError(f"Failed to download Drive file {file_id}.") from exc
        finally:
            buffer.close()

        logger.info("drive_file_downloaded", file_id=file_id, path=str(destination))
        return destination

    @staticmethod
    def _sha256_sync(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
