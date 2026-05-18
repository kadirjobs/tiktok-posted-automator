from pathlib import Path

from app.core.config import Settings
from app.core.constants import PostStatus


def test_default_settings() -> None:
    settings = Settings()
    assert settings.app_name == "tiktok-posted-automator"
    assert settings.mongodb_db_name == "tiktok_automator"
    assert settings.drive_poll_interval_seconds == 90


def test_drive_not_configured_without_credentials() -> None:
    settings = Settings(
        GOOGLE_APPLICATION_CREDENTIALS="",
        DRIVE_SOURCE_FOLDER_ID="",
    )
    assert settings.drive_configured is False


def test_storage_path_coercion() -> None:
    settings = Settings(STORAGE_PATH="./storage")
    assert isinstance(settings.storage_path, Path)


def test_post_status_enum_values() -> None:
    assert PostStatus.QUEUED.value == "queued"
    assert PostStatus.FAILED.value == "failed"
