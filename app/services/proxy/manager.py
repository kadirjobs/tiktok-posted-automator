from datetime import UTC, datetime

from app.core.constants import ProxyStatus
from app.core.database import get_database
from app.core.exceptions import ProxyError
from app.core.logger import get_logger
from app.core.security import decrypt_value
from app.models.account import ProxyConfig
from app.models.proxy import ProxyAssignRequest, StandbyProxy
from app.repositories.accounts_repo import AccountsRepository
from app.repositories.proxy_repo import ProxyRepository
from app.services.proxy.checker import ProxyChecker

logger = get_logger(__name__)


class ProxyManager:
    """Manages per-account proxies and the standby pool."""

    def __init__(self) -> None:
        db = get_database()
        self._accounts = AccountsRepository(db)
        self._proxies = ProxyRepository(db)
        self._checker = ProxyChecker()

    async def assign_proxy_to_account(
        self,
        account_name: str,
        request: ProxyAssignRequest,
        *,
        run_health_check: bool = True,
    ) -> dict[str, object]:
        account = await self._accounts.get_by_name(account_name)
        if not account:
            raise ProxyError(f"Account not found: {account_name}")

        proxy = ProxyConfig(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            status=ProxyStatus.WARMING,
        )

        if run_health_check:
            health = await self._checker.check(proxy)
            if not health.healthy:
                raise ProxyError(
                    f"Proxy health check failed: {health.error or 'unhealthy'}"
                )
            proxy.status = ProxyStatus.ACTIVE
            proxy.last_check_at = datetime.now(UTC)

        account_id = str(account["_id"])
        await self._accounts.update_proxy(account_id, proxy)
        logger.info("proxy_assigned", account_name=account_name, host=request.host)
        return {
            "account_name": account_name,
            "proxy_status": proxy.status.value,
            "latency_ms": health.latency_ms if run_health_check else None,
        }

    async def add_standby_proxy(self, request: ProxyAssignRequest) -> str:
        proxy = StandbyProxy(
            host=request.host,
            port=request.port,
            username=request.username,
            password=request.password,
            status=ProxyStatus.WARMING,
        )
        health = await self._checker.check(
            ProxyConfig(
                host=request.host,
                port=request.port,
                username=request.username,
                password=request.password,
            )
        )
        if not health.healthy:
            raise ProxyError(f"Standby proxy health check failed: {health.error or 'unhealthy'}")

        proxy.status = ProxyStatus.ACTIVE
        proxy_id = await self._proxies.add_standby(proxy)
        logger.info("standby_proxy_added", proxy_id=proxy_id, host=request.host)
        return proxy_id

    async def get_account_proxy(self, account_name: str) -> ProxyConfig:
        account = await self._accounts.get_by_name(account_name)
        if not account:
            raise ProxyError(f"Account not found: {account_name}")

        raw = account.get("proxy") or {}
        password = raw.get("password", "")
        if password:
            try:
                password = decrypt_value(password)
            except Exception:
                password = raw.get("password", "")

        return ProxyConfig(
            host=raw.get("host", ""),
            port=int(raw.get("port") or 0),
            username=raw.get("username", ""),
            password=password,
            status=ProxyStatus(raw.get("status", ProxyStatus.ACTIVE.value)),
        )

    async def standby_pool_status(self) -> dict[str, int]:
        active = await self._proxies.count_by_status(ProxyStatus.ACTIVE)
        warming = await self._proxies.count_by_status(ProxyStatus.WARMING)
        return {"active": active, "warming": warming}
