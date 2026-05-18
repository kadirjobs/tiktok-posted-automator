from typing import Any

import aiohttp

from app.core.config import Settings, get_settings
from app.core.exceptions import ProxyError
from app.core.logger import get_logger
from app.models.proxy import StandbyProxy

logger = get_logger(__name__)


class ProxyProviderClient:
    """
    Fetches new proxies from an external provider API.

    MVP: returns None when provider is not configured; operators assign proxies manually.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self._settings.proxy_provider_api_key and self._settings.proxy_provider_base_url)

    async def fetch_new_proxy(self) -> StandbyProxy | None:
        if not self.configured:
            logger.info("proxy_provider_not_configured")
            return None

        url = f"{self._settings.proxy_provider_base_url.rstrip('/')}/proxies"
        headers = {"Authorization": f"Bearer {self._settings.proxy_provider_api_key}"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        raise ProxyError(f"Proxy provider error {resp.status}: {body}")
                    data: dict[str, Any] = await resp.json()
        except aiohttp.ClientError as exc:
            raise ProxyError("Proxy provider request failed.") from exc

        return StandbyProxy(
            host=data["host"],
            port=int(data["port"]),
            username=data.get("username", ""),
            password=data.get("password", ""),
            geo=data.get("geo", ""),
        )
