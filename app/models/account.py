from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import AccountStatus, ProxyStatus


class ProxyConfig(BaseModel):
    host: str = ""
    port: int = 0
    username: str = ""
    password: str = ""
    status: ProxyStatus = ProxyStatus.ACTIVE
    last_check_at: datetime | None = None


class AccountAuth(BaseModel):
    access_token: str = ""
    refresh_token: str = ""
    expires_at: datetime | None = None
    refresh_lock: bool = False
    refresh_started_at: datetime | None = None


class AccountSettings(BaseModel):
    daily_limit: int = 3
    timezone: str = "Europe/Istanbul"


class AccountStats(BaseModel):
    success_uploads: int = 0
    failed_uploads: int = 0
    last_upload_at: datetime | None = None


class Account(BaseModel):
    account_name: str
    tiktok_user_id: str = ""
    status: AccountStatus = AccountStatus.ACTIVE
    risk_score: int = 0
    daily_upload_count: int = 0
    cooldown_until: datetime | None = None
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    auth: AccountAuth = Field(default_factory=AccountAuth)
    settings: AccountSettings = Field(default_factory=AccountSettings)
    stats: AccountStats = Field(default_factory=AccountStats)
