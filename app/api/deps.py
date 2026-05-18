import bcrypt
from fastapi import HTTPException, Request, status

from app.core.config import get_settings
from app.core.exceptions import AdminAuthError


def verify_admin_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def hash_admin_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


async def require_admin(request: Request) -> None:
    if not request.session.get("admin_authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required.",
        )


async def authenticate_admin(username: str, password: str) -> None:
    settings = get_settings()
    if not settings.admin_configured:
        raise AdminAuthError(
            "Admin credentials not configured. Set ADMIN_USERNAME and ADMIN_PASSWORD_HASH."
        )
    if username != settings.admin_username:
        raise AdminAuthError("Invalid credentials.")
    if not verify_admin_password(password, settings.admin_password_hash):
        raise AdminAuthError("Invalid credentials.")
