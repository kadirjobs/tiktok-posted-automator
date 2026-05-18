import base64
import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

import aiohttp

from app.core.config import Settings, get_settings
from app.core.constants import REDIS_OAUTH_STATE_PREFIX, TIKTOK_AUTH_URL, TIKTOK_TOKEN_URL
from app.core.database import get_redis
from app.core.exceptions import TikTokAuthError
from app.core.logger import get_logger

logger = get_logger(__name__)

OAUTH_STATE_TTL_SECONDS = 600


class TikTokAuthService:
    """TikTok OAuth 2.0 with PKCE for account onboarding."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @staticmethod
    def _generate_pkce_pair() -> tuple[str, str]:
        verifier = secrets.token_urlsafe(64)
        challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            .decode()
            .rstrip("=")
        )
        return verifier, challenge

    async def create_authorization_url(self, account_name: str) -> str:
        if not self._settings.tiktok_configured:
            raise TikTokAuthError(
                "TikTok is not configured. Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, "
                "and TIKTOK_REDIRECT_URI in .env."
            )

        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self._generate_pkce_pair()

        redis = get_redis()
        payload = json.dumps(
            {"account_name": account_name, "code_verifier": code_verifier}
        )
        await redis.setex(f"{REDIS_OAUTH_STATE_PREFIX}{state}", OAUTH_STATE_TTL_SECONDS, payload)

        params = {
            "client_key": self._settings.tiktok_client_key,
            "scope": self._settings.tiktok_scope_list,
            "response_type": "code",
            "redirect_uri": self._settings.tiktok_redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{TIKTOK_AUTH_URL}?{urlencode(params)}"

    async def consume_state(self, state: str) -> dict[str, str]:
        redis = get_redis()
        key = f"{REDIS_OAUTH_STATE_PREFIX}{state}"
        raw = await redis.get(key)
        if not raw:
            raise TikTokAuthError("Invalid or expired OAuth state (CSRF protection).")
        await redis.delete(key)
        return json.loads(raw)

    async def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        data = {
            "client_key": self._settings.tiktok_client_key,
            "client_secret": self._settings.tiktok_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._settings.tiktok_redirect_uri,
            "code_verifier": code_verifier,
        }
        return await self._token_request(data)

    async def refresh_tokens(self, refresh_token: str) -> dict[str, Any]:
        data = {
            "client_key": self._settings.tiktok_client_key,
            "client_secret": self._settings.tiktok_client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
        return await self._token_request(data)

    async def _token_request(self, data: dict[str, str]) -> dict[str, Any]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    TIKTOK_TOKEN_URL, data=data, headers=headers
                ) as response:
                    body = await response.json(content_type=None)
        except aiohttp.ClientError as exc:
            logger.error("tiktok_token_request_failed", error=str(exc))
            raise TikTokAuthError("TikTok token request failed.") from exc

        if response.status >= 400:
            logger.error("tiktok_token_error", status=response.status, body=body)
            raise TikTokAuthError(f"TikTok token error: {body}")

        token_data = body.get("data") or body
        if "access_token" not in token_data:
            raise TikTokAuthError(f"Unexpected TikTok token response: {body}")

        return token_data

    @staticmethod
    def expires_at_from_response(token_data: dict[str, Any]) -> datetime:
        expires_in = int(token_data.get("expires_in", 86400))
        return datetime.now(UTC) + timedelta(seconds=expires_in)
