from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import authenticate_admin, require_admin
from app.core.exceptions import AdminAuthError, TikTokAuthError
from app.core.logger import get_logger
from app.services.tiktok.auth import TikTokAuthService

logger = get_logger(__name__)

router = APIRouter(tags=["admin-auth"])


@router.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page() -> str:
    return """
    <html><body style="font-family:sans-serif;max-width:420px;margin:40px auto;">
    <h2>TikTok Automator — Admin</h2>
    <form method="post" action="/admin/login">
      <label>Username<br><input name="username" required></label><br><br>
      <label>Password<br><input name="password" type="password" required></label><br><br>
      <button type="submit">Login</button>
    </form>
    </body></html>
    """


@router.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
) -> RedirectResponse:
    try:
        await authenticate_admin(username, password)
    except AdminAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    request.session["admin_authenticated"] = True
    logger.info("admin_login_success", username=username)
    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/admin/logout")
async def admin_logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    _: None = Depends(require_admin),
) -> str:
    return """
    <html><body style="font-family:sans-serif;max-width:640px;margin:40px auto;">
    <h2>Admin Dashboard</h2>
    <ul>
      <li><a href="/admin/accounts">Hesaplar</a></li>
      <li><a href="/auth/tiktok/connect?account_name=personal">TikTok hesabı bağla (personal)</a></li>
    </ul>
    <form method="post" action="/admin/logout"><button type="submit">Logout</button></form>
    </body></html>
    """


@router.get("/auth/tiktok/connect")
async def tiktok_connect(
    account_name: str,
    _: None = Depends(require_admin),
) -> RedirectResponse:
    try:
        auth_url = await TikTokAuthService().create_authorization_url(account_name)
    except TikTokAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RedirectResponse(url=auth_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
