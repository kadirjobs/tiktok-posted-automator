from enum import StrEnum


class PostStatus(StrEnum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    DISTRIBUTING = "distributing"
    PARTIALLY_COMPLETED = "partially_completed"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"
    ARCHIVED = "archived"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    RATE_LIMITED = "rate_limited"
    PROXY_FAILED = "proxy_failed"
    TOKEN_EXPIRED = "token_expired"
    RE_AUTH_REQUIRED = "re_auth_required"
    SUSPENDED = "suspended"
    DEAD = "dead"


class UploadJobStatus(StrEnum):
    QUEUED = "queued"
    PREPARING = "preparing"
    UPLOADING = "uploading"
    PUBLISHING = "publishing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"


class ProxyStatus(StrEnum):
    ACTIVE = "active"
    WARMING = "warming"
    DEGRADED = "degraded"
    DEAD = "dead"


# MongoDB collection names
COLLECTION_ACCOUNTS = "accounts"
COLLECTION_POSTS = "posts"
COLLECTION_UPLOAD_JOBS = "upload_jobs"
COLLECTION_DRIVE_SYNC_STATE = "drive_sync_state"
COLLECTION_DRIVE_PENDING_FILES = "drive_pending_files"
COLLECTION_STANDBY_PROXIES = "standby_proxies"

# TikTok OAuth
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
TIKTOK_DEFAULT_SCOPES = "user.info.basic,video.upload,video.publish"
TOKEN_REFRESH_THRESHOLD_SECONDS = 1200  # 20 minutes

# Redis key prefixes
REDIS_OAUTH_STATE_PREFIX = "oauth:state:"
REDIS_TOKEN_REFRESH_LOCK_PREFIX = "lock:token_refresh:"

# Drive sync document id
DRIVE_SYNC_STATE_ID = "drive_sync"

# Supported media extensions
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
CAPTION_EXTENSION = ".txt"
