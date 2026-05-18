from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import Settings, get_settings
from app.core.constants import AccountStatus
from app.core.database import get_database
from app.core.exceptions import TikTokAuthError
from app.core.locking import redis_lock, token_refresh_lock_key
from app.core.logger import get_logger
from app.repositories.accounts_repo import AccountsRepository
from app.services.tiktok.auth import TikTokAuthService

logger = get_logger(__name__)


class TokenManager:
    """Ensures valid TikTok access tokens with distributed refresh locking."""

    def __init__(
        self,
        settings: Settings | None = None,
        accounts_repo: AccountsRepository | None = None,
        auth_service: TikTokAuthService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._accounts = accounts_repo or AccountsRepository(get_database())
        self._auth = auth_service or TikTokAuthService(self._settings)

    def _needs_refresh(self, account_doc: dict[str, Any]) -> bool:
        auth = account_doc.get("auth") or {}
        expires_at = auth.get("expires_at")
        if not expires_at:
            return True
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        threshold = datetime.now(UTC) + timedelta(
            seconds=self._settings.token_refresh_threshold_seconds
        )
        return expires_at <= threshold

    async def get_valid_access_token(self, account_id: str) -> str:
        account_doc = await self._accounts.get_by_id(account_id)
        if not account_doc:
            raise TikTokAuthError(f"Account not found: {account_id}")

        if not self._needs_refresh(account_doc):
            access, _ = await self._accounts.get_decrypted_tokens(account_doc)
            if access:
                return access

        await self.refresh_account_token(account_id)
        account_doc = await self._accounts.get_by_id(account_id)
        if not account_doc:
            raise TikTokAuthError(f"Account not found after refresh: {account_id}")
        access, _ = await self._accounts.get_decrypted_tokens(account_doc)
        if not access:
            raise TikTokAuthError("Access token unavailable after refresh.")
        return access

    async def refresh_account_token(self, account_id: str) -> None:
        lock_key = token_refresh_lock_key(account_id)
        async with redis_lock(lock_key, ttl_seconds=120) as acquired:
            if not acquired:
                logger.info("token_refresh_lock_busy", account_id=account_id)
                return

            account_doc = await self._accounts.get_by_id(account_id)
            if not account_doc:
                raise TikTokAuthError(f"Account not found: {account_id}")

            if not self._needs_refresh(account_doc):
                return

            _, refresh_token = await self._accounts.get_decrypted_tokens(account_doc)
            if not refresh_token:
                await self._accounts.set_status(account_id, AccountStatus.RE_AUTH_REQUIRED)
                raise TikTokAuthError("Refresh token missing — re-authentication required.")

            try:
                token_data = await self._auth.refresh_tokens(refresh_token)
                expires_at = TikTokAuthService.expires_at_from_response(token_data)
                await self._accounts.save_oauth_tokens(
                    account_id,
                    access_token=token_data["access_token"],
                    refresh_token=token_data.get("refresh_token", refresh_token),
                    expires_at=expires_at,
                    tiktok_user_id=token_data.get("open_id", account_doc.get("tiktok_user_id", "")),
                )
                logger.info("token_refreshed", account_id=account_id)
            except TikTokAuthError as exc:
                await self._accounts.increment_risk_score(account_id, 30)
                await self._accounts.set_status(account_id, AccountStatus.TOKEN_EXPIRED)
                logger.error("token_refresh_failed", account_id=account_id, error=str(exc))
                raise
