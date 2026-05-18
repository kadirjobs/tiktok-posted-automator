from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.constants import COLLECTION_ACCOUNTS, AccountStatus
from app.core.security import decrypt_value, encrypt_value
from app.models.account import Account, AccountAuth, ProxyConfig


class AccountsRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db[COLLECTION_ACCOUNTS]

    async def get_by_id(self, account_id: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"_id": ObjectId(account_id)})

    async def get_by_name(self, account_name: str) -> dict[str, Any] | None:
        return await self._collection.find_one({"account_name": account_name})

    async def list_accounts(self) -> list[dict[str, Any]]:
        cursor = self._collection.find({}, {"auth.access_token": 0, "auth.refresh_token": 0})
        return await cursor.to_list(length=500)

    async def create_account(self, account_name: str) -> str:
        account = Account(account_name=account_name)
        payload = account.model_dump(mode="json", exclude_none=True)
        result = await self._collection.insert_one(payload)
        return str(result.inserted_id)

    async def ensure_account(self, account_name: str) -> str:
        existing = await self.get_by_name(account_name)
        if existing:
            return str(existing["_id"])
        return await self.create_account(account_name)

    async def save_oauth_tokens(
        self,
        account_id: str,
        *,
        access_token: str,
        refresh_token: str,
        expires_at: datetime,
        tiktok_user_id: str,
    ) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(account_id)},
            {
                "$set": {
                    "tiktok_user_id": tiktok_user_id,
                    "status": AccountStatus.ACTIVE.value,
                    "auth.access_token": encrypt_value(access_token),
                    "auth.refresh_token": encrypt_value(refresh_token),
                    "auth.expires_at": expires_at,
                    "auth.refresh_lock": False,
                    "auth.refresh_started_at": None,
                }
            },
        )

    async def get_decrypted_tokens(self, account_doc: dict[str, Any]) -> tuple[str, str]:
        auth = account_doc.get("auth") or {}
        access = decrypt_value(auth.get("access_token", ""))
        refresh = decrypt_value(auth.get("refresh_token", ""))
        return access, refresh

    async def update_proxy(self, account_id: str, proxy: ProxyConfig) -> None:
        payload = proxy.model_dump(mode="json", exclude_none=True)
        if proxy.password:
            payload["password"] = encrypt_value(proxy.password)
        await self._collection.update_one(
            {"_id": ObjectId(account_id)},
            {"$set": {"proxy": payload}},
        )

    async def set_refresh_lock(self, account_id: str, locked: bool) -> bool:
        now = datetime.now(UTC)
        result = await self._collection.update_one(
            {
                "_id": ObjectId(account_id),
                "auth.refresh_lock": {"$ne": locked},
            },
            {
                "$set": {
                    "auth.refresh_lock": locked,
                    "auth.refresh_started_at": now if locked else None,
                }
            },
        )
        return result.modified_count > 0

    async def increment_risk_score(self, account_id: str, amount: int) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(account_id)},
            {"$inc": {"risk_score": amount}},
        )

    async def set_status(self, account_id: str, status: AccountStatus) -> None:
        await self._collection.update_one(
            {"_id": ObjectId(account_id)},
            {"$set": {"status": status.value}},
        )
