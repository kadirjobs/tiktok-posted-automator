from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import Settings, get_settings
from app.core.constants import CAPTION_EXTENSION, PostStatus, VIDEO_EXTENSIONS
from app.core.exceptions import DriveNotConfiguredError, DriveSyncError
from app.core.logger import get_logger
from app.core.database import get_database
from app.models.drive import DrivePendingFile
from app.repositories.drive_repo import DriveRepository
from app.repositories.posts_repo import PostsRepository
from app.services.drive.downloader import DriveDownloader

logger = get_logger(__name__)

DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive"]
MEDIA_MIME_PREFIX = "video/"


@dataclass(frozen=True)
class DriveFileSnapshot:
    file_id: str
    name: str
    mime_type: str
    size: int
    modified_time: str
    base_name: str


class DriveWatcher:
    """
    Incremental Google Drive sync skeleton.

  Uses Changes API with persisted last_change_token.
  Enforces settle-time before files enter the download pipeline.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        drive_repo: DriveRepository | None = None,
        posts_repo: PostsRepository | None = None,
        downloader: DriveDownloader | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._drive_repo = drive_repo
        self._posts_repo = posts_repo
        self._downloader = downloader or DriveDownloader(self._settings)

    def _repos(self) -> tuple[DriveRepository, PostsRepository]:
        db = get_database()
        drive_repo = self._drive_repo or DriveRepository(db)
        posts_repo = self._posts_repo or PostsRepository(db)
        return drive_repo, posts_repo

    def _build_drive_service(self) -> Any:
        if not self._settings.drive_configured:
            raise DriveNotConfiguredError(
                "Google Drive is not configured. Set GOOGLE_APPLICATION_CREDENTIALS "
                "and DRIVE_SOURCE_FOLDER_ID in .env."
            )
        credentials = service_account.Credentials.from_service_account_file(
            self._settings.google_application_credentials,
            scopes=DRIVE_SCOPES,
        )
        return build("drive", "v3", credentials=credentials, cache_discovery=False)

    @staticmethod
    def _base_name(filename: str) -> str:
        path = Path(filename)
        if path.suffix.lower() in VIDEO_EXTENSIONS:
            return path.stem
        if path.suffix.lower() == CAPTION_EXTENSION:
            return path.stem
        return path.stem

    @staticmethod
    def _is_video_file(name: str, mime_type: str) -> bool:
        suffix = Path(name).suffix.lower()
        return suffix in VIDEO_EXTENSIONS or mime_type.startswith(MEDIA_MIME_PREFIX)

    @staticmethod
    def _is_caption_file(name: str) -> bool:
        return Path(name).suffix.lower() == CAPTION_EXTENSION

    async def run_sync_cycle(self) -> dict[str, int]:
        """
        Execute one incremental sync cycle.

        Returns counters for observability.
        """
        drive_repo, posts_repo = self._repos()
        stats = {
            "changes_seen": 0,
            "pending_updated": 0,
            "pairs_ready": 0,
            "posts_registered": 0,
            "skipped_unstable": 0,
            "downloads_completed": 0,
        }

        if not self._settings.drive_configured:
            logger.warning("drive_sync_skipped", reason="not_configured")
            return stats

        service = self._build_drive_service()
        sync_state = await drive_repo.get_sync_state()
        page_token = sync_state.last_change_token or None

        try:
            if not page_token:
                page_token = (
                    service.changes()
                    .getStartPageToken(supportsAllDrives=True)
                    .execute()
                    .get("startPageToken")
                )

            while page_token:
                response = (
                    service.changes()
                    .list(
                        pageToken=page_token,
                        spaces="drive",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        fields=(
                            "nextPageToken,newStartPageToken,"
                            "changes(fileId,removed,file(id,name,mimeType,size,modifiedTime,parents,trashed))"
                        ),
                    )
                    .execute()
                )

                for change in response.get("changes", []):
                    stats["changes_seen"] += 1
                    await self._process_change(change, drive_repo, posts_repo, stats)

                page_token = response.get("nextPageToken")
                new_start = response.get("newStartPageToken")
                if new_start:
                    await drive_repo.save_change_token(new_start)
                    break

        except HttpError as exc:
            logger.error("drive_sync_http_error", status=exc.resp.status, detail=str(exc))
            raise DriveSyncError("Google Drive Changes API request failed.") from exc
        except DriveNotConfiguredError:
            raise
        except Exception as exc:
            logger.error("drive_sync_failed", error=str(exc))
            raise DriveSyncError("Drive sync cycle failed.") from exc

        logger.info("drive_sync_cycle_completed", **stats)
        return stats

    async def _process_change(
        self,
        change: dict[str, Any],
        drive_repo: DriveRepository,
        posts_repo: PostsRepository,
        stats: dict[str, int],
    ) -> None:
        if change.get("removed"):
            return

        file_meta = change.get("file") or {}
        if file_meta.get("trashed"):
            return

        parents = file_meta.get("parents") or []
        if self._settings.drive_source_folder_id not in parents:
            return

        snapshot = self._to_snapshot(file_meta)
        if not self._is_video_file(snapshot.name, snapshot.mime_type) and not self._is_caption_file(
            snapshot.name
        ):
            return

        existing_post = await posts_repo.find_by_drive_file_id(snapshot.file_id)
        if existing_post:
            return

        await self._track_settle_time(snapshot, drive_repo, stats)
        await self._attempt_pair_registration(snapshot, drive_repo, posts_repo, stats)

    async def _track_settle_time(
        self,
        snapshot: DriveFileSnapshot,
        drive_repo: DriveRepository,
        stats: dict[str, int],
    ) -> None:
        now = datetime.now(UTC)
        pending = await drive_repo.get_pending_file(snapshot.file_id)

        is_video = self._is_video_file(snapshot.name, snapshot.mime_type)
        if pending is None:
            pending = DrivePendingFile(
                file_id=snapshot.file_id,
                base_name=snapshot.base_name,
                is_video=is_video,
                mime_type=snapshot.mime_type,
                size=snapshot.size,
                modified_time=snapshot.modified_time,
                stable_cycles=0,
                first_seen_at=now,
                last_checked_at=now,
            )
        else:
            pending.is_video = is_video
            unchanged = (
                pending.size == snapshot.size
                and pending.modified_time == snapshot.modified_time
            )
            if unchanged:
                pending.stable_cycles += 1
            else:
                pending.stable_cycles = 0
                pending.size = snapshot.size
                pending.modified_time = snapshot.modified_time

            pending.last_checked_at = now

        await drive_repo.upsert_pending_file(pending)
        stats["pending_updated"] += 1

        if pending.stable_cycles < self._settings.drive_stable_cycles_required:
            stats["skipped_unstable"] += 1

    def _is_settled(self, pending: DrivePendingFile) -> bool:
        if pending.stable_cycles < self._settings.drive_stable_cycles_required:
            return False
        if not pending.first_seen_at:
            return False
        elapsed = (datetime.now(UTC) - pending.first_seen_at).total_seconds()
        return elapsed >= self._settings.drive_settle_window_seconds

    async def _attempt_pair_registration(
        self,
        snapshot: DriveFileSnapshot,
        drive_repo: DriveRepository,
        posts_repo: PostsRepository,
        stats: dict[str, int],
    ) -> None:
        pending = await drive_repo.get_pending_file(snapshot.file_id)
        if not pending or not self._is_settled(pending):
            return

        pair_members = await drive_repo.find_pending_by_base_name(snapshot.base_name)
        video_pending = self._pick_pair_member(pair_members, is_video=True)
        caption_pending = self._pick_pair_member(pair_members, is_video=False)

        if not video_pending or not caption_pending:
            return
        if not self._is_settled(video_pending) or not self._is_settled(caption_pending):
            return

        existing = await posts_repo.find_by_drive_file_id(video_pending.file_id)
        if existing:
            return

        stats["pairs_ready"] += 1
        sync_state = await drive_repo.get_sync_state()
        post_id = await posts_repo.create_from_drive(
            video_file_id=video_pending.file_id,
            change_token=sync_state.last_change_token,
            caption="",
        )

        storage_dir = self._downloader.build_post_storage_dir(post_id)
        video_path = storage_dir / "video.mp4"
        caption_path = storage_dir / "caption.txt"

        await posts_repo.update_status(post_id, PostStatus.DOWNLOADING)
        await self._downloader.download_video(video_pending.file_id, video_path)
        _, caption_text = await self._downloader.download_caption(
            caption_pending.file_id, caption_path
        )
        checksum = await self._downloader.sha256_file(video_path)
        await posts_repo.update_after_download(
            post_id,
            video_path=str(video_path),
            caption_path=str(caption_path),
            caption=caption_text,
            checksum_sha256=checksum,
            status=PostStatus.DOWNLOADED,
        )

        await drive_repo.delete_pending_file(video_pending.file_id)
        await drive_repo.delete_pending_file(caption_pending.file_id)

        stats["posts_registered"] += 1
        stats["downloads_completed"] += 1
        logger.info(
            "drive_pair_registered",
            post_id=post_id,
            base_name=snapshot.base_name,
            video_file_id=video_pending.file_id,
            caption_file_id=caption_pending.file_id,
        )

    @staticmethod
    def _pick_pair_member(
        members: list[DrivePendingFile],
        *,
        is_video: bool,
    ) -> DrivePendingFile | None:
        for member in members:
            if member.is_video == is_video:
                return member
        return None

    def _to_snapshot(self, file_meta: dict[str, Any]) -> DriveFileSnapshot:
        name = file_meta.get("name", "")
        return DriveFileSnapshot(
            file_id=file_meta["id"],
            name=name,
            mime_type=file_meta.get("mimeType", ""),
            size=int(file_meta.get("size") or 0),
            modified_time=file_meta.get("modifiedTime", ""),
            base_name=self._base_name(name),
        )
