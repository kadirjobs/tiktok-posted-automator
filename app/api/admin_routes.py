from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_admin
from app.core.database import get_database
from app.core.exceptions import ProxyError, TikTokAuthError
from app.core.logger import get_logger
from app.models.proxy import ProxyAssignRequest
from app.repositories.accounts_repo import AccountsRepository
from app.services.drive.watcher import DriveWatcher
from app.services.proxy.manager import ProxyManager
from app.services.proxy.rotator import ProxyRotator
from app.services.tiktok.token_manager import TokenManager

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/accounts")
async def list_accounts() -> list[dict[str, Any]]:
    repo = AccountsRepository(get_database())
    accounts = await repo.list_accounts()
    for account in accounts:
        account["_id"] = str(account["_id"])
        proxy = account.get("proxy") or {}
        if proxy.get("password"):
            proxy["password"] = "***"
    return accounts


@router.post("/accounts/{account_name}")
async def create_account(account_name: str) -> dict[str, str]:
    repo = AccountsRepository(get_database())
    existing = await repo.get_by_name(account_name)
    if existing:
        return {"account_id": str(existing["_id"]), "status": "exists"}
    account_id = await repo.create_account(account_name)
    return {"account_id": account_id, "status": "created"}


@router.post("/accounts/{account_name}/proxy")
async def assign_account_proxy(
    account_name: str,
    body: ProxyAssignRequest,
) -> dict[str, object]:
    try:
        return await ProxyManager().assign_proxy_to_account(account_name, body)
    except ProxyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/proxy/standby")
async def add_standby_proxy(body: ProxyAssignRequest) -> dict[str, str]:
    try:
        proxy_id = await ProxyManager().add_standby_proxy(body)
        return {"proxy_id": proxy_id, "status": "added"}
    except ProxyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/proxy/standby/status")
async def standby_status() -> dict[str, int]:
    return await ProxyManager().standby_pool_status()


@router.post("/accounts/{account_name}/proxy/rotate")
async def rotate_proxy(account_name: str) -> dict[str, str]:
    try:
        return await ProxyRotator().replace_account_proxy(account_name)
    except ProxyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/accounts/{account_name}/token/refresh")
async def refresh_token(account_name: str) -> dict[str, str]:
    repo = AccountsRepository(get_database())
    account = await repo.get_by_name(account_name)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found.")
    try:
        await TokenManager().refresh_account_token(str(account["_id"]))
    except TikTokAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"status": "refreshed", "account_name": account_name}


@router.post("/drive/sync")
async def trigger_drive_sync() -> dict[str, int]:
    stats = await DriveWatcher().run_sync_cycle()
    return stats
