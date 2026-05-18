from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="tiktok-posted-automator", alias="APP_NAME")
    secret_key: str = Field(default="dev-secret-change-me", alias="SECRET_KEY")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    fernet_key: str = Field(default="", alias="FERNET_KEY")

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        alias="MONGODB_URI",
    )
    mongodb_db_name: str = Field(
        default="tiktok_automator",
        alias="MONGODB_DB_NAME",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    storage_path: Path = Field(default=Path("./storage"), alias="STORAGE_PATH")

    google_application_credentials: str = Field(
        default="",
        alias="GOOGLE_APPLICATION_CREDENTIALS",
    )
    drive_source_folder_id: str = Field(default="", alias="DRIVE_SOURCE_FOLDER_ID")
    drive_archive_folder_id: str = Field(default="", alias="DRIVE_ARCHIVE_FOLDER_ID")
    drive_poll_interval_seconds: int = Field(
        default=90,
        ge=60,
        le=120,
        alias="DRIVE_POLL_INTERVAL_SECONDS",
    )
    drive_settle_window_seconds: int = Field(
        default=180,
        ge=120,
        le=300,
        alias="DRIVE_SETTLE_WINDOW_SECONDS",
    )
    drive_stable_cycles_required: int = Field(
        default=2,
        ge=1,
        le=5,
        alias="DRIVE_STABLE_CYCLES_REQUIRED",
    )

    tiktok_client_key: str = Field(default="", alias="TIKTOK_CLIENT_KEY")
    tiktok_client_secret: str = Field(default="", alias="TIKTOK_CLIENT_SECRET")
    tiktok_redirect_uri: str = Field(default="", alias="TIKTOK_REDIRECT_URI")

    proxy_provider_api_key: str = Field(default="", alias="PROXY_PROVIDER_API_KEY")
    proxy_provider_base_url: str = Field(default="", alias="PROXY_PROVIDER_BASE_URL")

    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field(default="", alias="TELEGRAM_CHAT_ID")

    sentry_dsn: str = Field(default="", alias="SENTRY_DSN")

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password_hash: str = Field(default="", alias="ADMIN_PASSWORD_HASH")

    tiktok_scopes: str = Field(default="", alias="TIKTOK_SCOPES")
    token_refresh_threshold_seconds: int = Field(
        default=1200,
        alias="TOKEN_REFRESH_THRESHOLD_SECONDS",
    )
    proxy_health_check_interval_seconds: int = Field(
        default=600,
        alias="PROXY_HEALTH_CHECK_INTERVAL_SECONDS",
    )
    standby_proxy_min_count: int = Field(default=1, alias="STANDBY_PROXY_MIN_COUNT")

    @field_validator("storage_path", mode="before")
    @classmethod
    def _coerce_storage_path(cls, value: str | Path) -> Path:
        return Path(value)

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def drive_configured(self) -> bool:
        return bool(
            self.google_application_credentials
            and self.drive_source_folder_id
            and Path(self.google_application_credentials).exists()
        )

    def ensure_storage_dir(self) -> Path:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        return self.storage_path

    @property
    def tiktok_configured(self) -> bool:
        return bool(
            self.tiktok_client_key
            and self.tiktok_client_secret
            and self.tiktok_redirect_uri
        )

    @property
    def tiktok_scope_list(self) -> str:
        from app.core.constants import TIKTOK_DEFAULT_SCOPES

        return self.tiktok_scopes or TIKTOK_DEFAULT_SCOPES

    @property
    def admin_configured(self) -> bool:
        return bool(self.admin_username and self.admin_password_hash)


@lru_cache
def get_settings() -> Settings:
    return Settings()
