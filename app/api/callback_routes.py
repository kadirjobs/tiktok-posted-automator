from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import HTMLResponse

from app.core.database import get_database
from app.core.exceptions import TikTokAuthError
from app.core.logger import get_logger
from app.repositories.accounts_repo import AccountsRepository
from app.services.tiktok.auth import TikTokAuthService

logger = get_logger(__name__)

router = APIRouter(tags=["oauth"])


@router.get("/auth/tiktok/callback", response_class=HTMLResponse)
async def tiktok_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> str:
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"TikTok OAuth error: {error}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter.",
        )

    auth_service = TikTokAuthService()
    accounts_repo = AccountsRepository(get_database())

    try:
        oauth_ctx = await auth_service.consume_state(state)
        token_data = await auth_service.exchange_code(code, oauth_ctx["code_verifier"])
        account_name = oauth_ctx["account_name"]
        account_id = await accounts_repo.ensure_account(account_name)
        expires_at = TikTokAuthService.expires_at_from_response(token_data)
        await accounts_repo.save_oauth_tokens(
            account_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_at=expires_at,
            tiktok_user_id=token_data.get("open_id", ""),
        )
    except TikTokAuthError as exc:
        logger.error("tiktok_oauth_callback_failed", error=str(exc))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    logger.info("tiktok_oauth_success", account_name=account_name)
    return f"""
    <html><body style="font-family:sans-serif;max-width:520px;margin:40px auto;">
    <h2>TikTok bağlantısı başarılı</h2>
    <p>Hesap: <strong>{account_name}</strong></p>
    <p>Token'lar şifrelenmiş olarak MongoDB'ye kaydedildi.</p>
    <p><a href="/admin/dashboard">Dashboard'a dön</a></p>
    </body></html>
    """
