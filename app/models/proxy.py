from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import ProxyStatus


class ProxyReputation(BaseModel):
    success_rate: float = 0.0
    avg_latency: float = 0.0
    ban_events: int = 0
    last_rotation_at: datetime | None = None


class StandbyProxy(BaseModel):
    host: str
    port: int
    username: str = ""
    password: str = ""
    status: ProxyStatus = ProxyStatus.WARMING
    geo: str = ""
    reputation: ProxyReputation = Field(default_factory=ProxyReputation)
    created_at: datetime | None = None
    last_check_at: datetime | None = None


class ProxyAssignRequest(BaseModel):
    host: str
    port: int
    username: str = ""
    password: str = ""
