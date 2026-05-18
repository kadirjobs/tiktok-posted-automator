from app.core.constants import CAPTION_EXTENSION, VIDEO_EXTENSIONS
from app.services.drive.watcher import DriveWatcher


def test_base_name_strips_video_extension() -> None:
    assert DriveWatcher._base_name("clip_001.mp4") == "clip_001"


def test_base_name_strips_caption_extension() -> None:
    assert DriveWatcher._base_name(f"clip_001{CAPTION_EXTENSION}") == "clip_001"


def test_is_video_file_by_extension() -> None:
    assert DriveWatcher._is_video_file("clip.mp4", "") is True
    assert ".mp4" in VIDEO_EXTENSIONS


def test_is_caption_file() -> None:
    assert DriveWatcher._is_caption_file(f"clip{CAPTION_EXTENSION}") is True
