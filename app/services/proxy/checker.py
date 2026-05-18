import time
from dataclasses import dataclass

import aiohttp

from app.core.logger import get_logger
from app.models.account import ProxyConfig

logger = get_logger(__name__)

TIKTOK_REACHABILITY_URL = "https://www.tiktok.com/"


@dataclass(frozen=True)
class ProxyHealthResult:
    healthy: bool
    latency_ms: float
    reachable: bool
    error: str = ""


class ProxyChecker:
    """Validates proxy latency and basic TikTok reachability."""

    async def check(self, proxy: ProxyConfig) -> ProxyHealthResult:
        proxy_url = self._build_proxy_url(proxy)
        started = time.perf_counter()
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    TIKTOK_REACHABILITY_URL,
                    proxy=proxy_url,
                    timeout=timeout,
                    allow_redirects=True,
                ) as response:
                    latency_ms = (time.perf_counter() - started) * 1000
                    reachable = response.status < 500
                    healthy = reachable and latency_ms < 5000
                    return ProxyHealthResult(
                        healthy=healthy,
                        latency_ms=round(latency_ms, 2),
                        reachable=reachable,
                    )
        except aiohttp.ClientError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.warning("proxy_health_check_failed", host=proxy.host, error=str(exc))
            return ProxyHealthResult(
                healthy=False,
                latency_ms=round(latency_ms, 2),
                reachable=False,
                error=str(exc),
            )

    @staticmethod
    def _build_proxy_url(proxy: ProxyConfig) -> str:
        if proxy.username and proxy.password:
            return f"http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}"
        return f"http://{proxy.host}:{proxy.port}"
