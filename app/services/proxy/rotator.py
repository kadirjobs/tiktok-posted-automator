from datetime import UTC, datetime

from app.core.constants import AccountStatus, ProxyStatus
from app.core.database import get_database
from app.core.exceptions import ProxyError
from app.core.logger import get_logger
from app.core.security import decrypt_value
from app.models.account import ProxyConfig
from app.repositories.accounts_repo import AccountsRepository
from app.repositories.proxy_repo import ProxyRepository
from app.services.proxy.checker import ProxyChecker
from app.services.proxy.provider_client import ProxyProviderClient

logger = get_logger(__name__)


class ProxyRotator:
    """Replaces failed account proxies using the standby pool."""

    def __init__(self) -> None:
        db = get_database()
        self._accounts = AccountsRepository(db)
        self._proxies = ProxyRepository(db)
        self._checker = ProxyChecker()
        self._provider = ProxyProviderClient()

    async def replace_account_proxy(self, account_name: str) -> dict[str, str]:
        account = await self._accounts.get_by_name(account_name)
        if not account:
            raise ProxyError(f"Account not found: {account_name}")

        standby = await self._proxies.pop_active_standby()
        if not standby:
            raise ProxyError("No active standby proxy available.")

        password = standby.get("password", "")
        if password:
            password = decrypt_value(password)

        proxy = ProxyConfig(
            host=standby["host"],
            port=int(standby["port"]),
            username=standby.get("username", ""),
            password=password,
            status=ProxyStatus.ACTIVE,
            last_check_at=datetime.now(UTC),
        )

        account_id = str(account["_id"])
        await self._accounts.update_proxy(account_id, proxy)
        await self._accounts.set_status(account_id, AccountStatus.ACTIVE)
        await self._accounts.increment_risk_score(account_id, 10)

        logger.info(
            "proxy_rotated",
            account_name=account_name,
            new_host=proxy.host,
            standby_id=str(standby["_id"]),
        )

        # Replenish standby pool in background later (Celery Phase 4).
        await self._try_replenish_standby()

        return {
            "account_name": account_name,
            "new_proxy_host": proxy.host,
            "standby_proxy_id": str(standby["_id"]),
        }

    async def _try_replenish_standby(self) -> None:
        new_proxy = await self._provider.fetch_new_proxy()
        if not new_proxy:
            logger.info("standby_replenish_skipped", reason="provider_not_configured")
            return

        health = await self._checker.check(
            ProxyConfig(
                host=new_proxy.host,
                port=new_proxy.port,
                username=new_proxy.username,
                password=new_proxy.password,
            )
        )
        if health.healthy:
            new_proxy.status = ProxyStatus.ACTIVE
            await self._proxies.add_standby(new_proxy)
            logger.info("standby_replenished", host=new_proxy.host)
