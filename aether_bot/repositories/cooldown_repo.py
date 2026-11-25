"""`cooldowns` хүснэгтийн Data Access Layer.

Бүх action-ийн cooldown нь UTC текстээр хадгалагдана. `remaining()` нь
service давхаргад `ActionCooldownError` шидэхэд бэлэн секунд буцаана.
"""

from __future__ import annotations

from datetime import timedelta

from core.database import Database
from utils.time_utils import from_db, seconds_until, to_db, utcnow


class CooldownRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_expires_at(self, user_id: int, action: str) -> str | None:
        value = await self.db.fetchval(
            "SELECT expires_at FROM cooldowns WHERE user_id = ? AND action_key = ?",
            (user_id, action),
        )
        return str(value) if value else None

    async def remaining(self, user_id: int, action: str) -> int:
        return seconds_until(from_db(await self.get_expires_at(user_id, action)))

    async def is_ready(self, user_id: int, action: str) -> bool:
        return await self.remaining(user_id, action) <= 0

    async def set(self, user_id: int, action: str, expires_at: str) -> None:
        await self.db.execute(
            """
            INSERT INTO cooldowns (user_id, action_key, expires_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, action_key) DO UPDATE SET
                expires_at = excluded.expires_at
            """,
            (user_id, action, expires_at),
        )

    async def set_for(self, user_id: int, action: str, seconds: int) -> str:
        expires = to_db(utcnow() + timedelta(seconds=max(0, int(seconds))))
        await self.set(user_id, action, expires)
        return expires

    async def clear(self, user_id: int, action: str) -> bool:
        return (
            await self.db.execute(
                "DELETE FROM cooldowns WHERE user_id = ? AND action_key = ?",
                (user_id, action),
            )
            == 1
        )

    async def clear_many(self, user_id: int, actions: tuple[str, ...]) -> int:
        if not actions:
            return 0
        placeholders = ",".join("?" for _ in actions)
        return await self.db.execute(
            f"DELETE FROM cooldowns WHERE user_id = ? AND action_key IN ({placeholders})",
            (user_id, *actions),
        )

    async def purge_expired(self) -> int:
        return await self.db.execute(
            "DELETE FROM cooldowns WHERE expires_at <= CURRENT_TIMESTAMP"
        )
