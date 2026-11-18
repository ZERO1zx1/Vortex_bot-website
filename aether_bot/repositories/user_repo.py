"""`users` хүснэгтийн Data Access Layer.

Зөвхөн SQL — бизнес дүрэм энд бичихгүй. Бүх метод `db.transaction()` дотор
дуудагдахад тухайн транзакцад автоматаар нэгдэнэ (core/database.py-г үз).
"""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

import config
from core.database import Database


@dataclass(frozen=True, slots=True)
class UserRow:
    user_id: int
    wallet: int
    bank: int
    xp: int
    level: int
    skill_points: int
    daily_streak: int
    casino_net: int
    last_daily_at: str | None
    shield_until: str | None
    active_title: str
    bio: str

    @property
    def net_worth(self) -> int:
        return self.wallet + self.bank

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> UserRow:
        return cls(
            user_id=row["user_id"],
            wallet=row["wallet"],
            bank=row["bank"],
            xp=row["xp"],
            level=row["level"],
            skill_points=row["skill_points"],
            daily_streak=row["daily_streak"],
            casino_net=row["casino_net"],
            last_daily_at=row["last_daily_at"],
            shield_until=row["shield_until"],
            active_title=row["active_title"],
            bio=row["bio"],
        )


_SELECT = """
    SELECT user_id, wallet, bank, xp, level, skill_points, daily_streak,
           casino_net, last_daily_at, shield_until, active_title, bio
      FROM users
"""


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, user_id: int) -> UserRow | None:
        row = await self.db.fetchone(f"{_SELECT} WHERE user_id = ?", (user_id,))
        return UserRow.from_row(row) if row else None

    async def get_or_create(self, user_id: int) -> UserRow:
        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, wallet) VALUES (?, ?)",
            (user_id, config.STARTING_WALLET),
        )
        row = await self.db.fetchone(f"{_SELECT} WHERE user_id = ?", (user_id,))
        if row is None:  # онолын хувьд боломжгүй
            raise RuntimeError(f"users мөр үүсгэж чадсангүй: {user_id}")
        return UserRow.from_row(row)

    async def get_many(self, user_ids: list[int]) -> dict[int, UserRow]:
        if not user_ids:
            return {}
        # SQLite-ийн variable limit-ээс зайлсхийхийн тулд chunk-лана.
        unique = list(dict.fromkeys(user_ids))
        result: dict[int, UserRow] = {}
        for start in range(0, len(unique), 500):
            chunk = unique[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = await self.db.fetchall(
                f"{_SELECT} WHERE user_id IN ({placeholders})", tuple(chunk)
            )
            result.update({row["user_id"]: UserRow.from_row(row) for row in rows})
        return result

    # ── Skill Point ────────────────────────────────────────────────────
    async def spend_skill_points(self, user_id: int, amount: int) -> bool:
        """Атомик шалгалт + хасалт. Хангалтгүй бол False."""
        if amount <= 0:
            raise ValueError("amount > 0 байх ёстой")
        affected = await self.db.execute(
            """
            UPDATE users
               SET skill_points = skill_points - ?,
                   updated_at   = datetime('now')
             WHERE user_id = ? AND skill_points >= ?
            """,
            (amount, user_id, amount),
        )
        return affected == 1

    async def grant_skill_points(self, user_id: int, amount: int) -> int:
        """SP нэмж, шинэ утгыг буцаана. (Level-up / reset-д ашиглагдана.)"""
        if amount < 0:
            raise ValueError("amount >= 0 байх ёстой")
        await self.db.execute(
            "UPDATE users SET skill_points = skill_points + ?, updated_at = datetime('now') WHERE user_id = ?",
            (amount, user_id),
        )
        return int(
            await self.db.fetchval(
                "SELECT skill_points FROM users WHERE user_id = ?", (user_id,), 0
            )
        )
