"""`users` хүснэгтийн Data Access Layer.

Зөвхөн SQL — бизнес дүрэм энд бичихгүй. Бүх метод `db.transaction()` дотор
дуудагдахад тухайн транзакцад автоматаар нэгдэнэ (core/database.py-г үз).
"""

from __future__ import annotations

from dataclasses import dataclass

import config
from core.database import Database, Row
from core.exceptions import UserNotFoundError


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
    jail_until: str | None = None
    jail_bail_cost: int = 0
    created_at: str | None = None
    updated_at: str | None = None

    @property
    def net_worth(self) -> int:
        return self.wallet + self.bank

    @property
    def is_jailed(self) -> bool:
        # Цагийн харьцуулалтыг service давхарга `from_db()`-ээр хийнэ; энэ
        # property зөвхөн "тэмдэглэгдсэн эсэх"-ийг хэлнэ.
        return self.jail_until is not None

    @classmethod
    def from_row(cls, row: Row) -> UserRow:
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
            jail_until=row["jail_until"],
            jail_bail_cost=row["jail_bail_cost"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


_SELECT = """
    SELECT user_id, wallet, bank, xp, level, skill_points, daily_streak,
           casino_net, last_daily_at, shield_until, active_title, bio,
           jail_until, jail_bail_cost, created_at, updated_at
      FROM users
"""

_LEADERBOARD_SQL = {
    "level": "level DESC, xp DESC",
    "wealth": "(wallet + bank) DESC, wallet DESC",
    "casino": "casino_net DESC, wallet DESC",
}


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, user_id: int) -> UserRow | None:
        row = await self.db.fetchone(f"{_SELECT} WHERE user_id = ?", (user_id,))
        return UserRow.from_row(row) if row else None

    async def get_or_create(self, user_id: int) -> UserRow:
        await self.db.execute(
            "INSERT INTO users (user_id, wallet) VALUES (?, ?) "
            "ON CONFLICT (user_id) DO NOTHING",
            (user_id, config.STARTING_WALLET),
        )
        row = await self.db.fetchone(f"{_SELECT} WHERE user_id = ?", (user_id,))
        if row is None:  # онолын хувьд боломжгүй
            raise RuntimeError(f"users мөр үүсгэж чадсангүй: {user_id}")
        return UserRow.from_row(row)

    async def get_many(self, user_ids: list[int]) -> dict[int, UserRow]:
        if not user_ids:
            return {}
        # Маш том IN query болон packet үүсгэхгүйгээр хэсэгчлэн уншина.
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

    async def _require(self, user_id: int) -> UserRow:
        user = await self.get(user_id)
        if user is None:
            raise UserNotFoundError()
        return user

    async def leaderboard(
        self, category: str = "level", limit: int = 10
    ) -> list[UserRow]:
        order = _LEADERBOARD_SQL.get(category)
        if order is None:
            raise ValueError(f"Invalid leaderboard category: {category}")
        rows = await self.db.fetchall(f"{_SELECT} ORDER BY {order} LIMIT ?", (limit,))
        return [UserRow.from_row(row) for row in rows]

    # ── Wallet / Bank ──────────────────────────────────────────────────
    async def credit_wallet(self, user_id: int, amount: int) -> int:
        """Wallet-д нэмж, шинэ утгыг буцаана."""
        if amount < 0:
            raise ValueError("amount >= 0 байх ёстой")
        value = await self.db.fetchval_write(
            """
            UPDATE users
               SET wallet = wallet + ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ?
            RETURNING wallet
            """,
            (amount, user_id),
        )
        if value is None:
            raise UserNotFoundError()
        return int(value)

    async def spend_wallet(self, user_id: int, amount: int) -> bool:
        """Атомик шалгалт + хасалт. Хангалтгүй бол False."""
        if amount <= 0:
            raise ValueError("amount > 0 байх ёстой")
        affected = await self.db.execute(
            """
            UPDATE users
               SET wallet = wallet - ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ? AND wallet >= ?
            """,
            (amount, user_id, amount),
        )
        return affected == 1

    async def credit_bank(self, user_id: int, amount: int) -> int:
        if amount < 0:
            raise ValueError("amount >= 0 байх ёстой")
        value = await self.db.fetchval_write(
            """
            UPDATE users
               SET bank = bank + ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ?
            RETURNING bank
            """,
            (amount, user_id),
        )
        if value is None:
            raise UserNotFoundError()
        return int(value)

    async def spend_bank(self, user_id: int, amount: int) -> bool:
        if amount <= 0:
            raise ValueError("amount > 0 байх ёстой")
        affected = await self.db.execute(
            """
            UPDATE users
               SET bank = bank - ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ? AND bank >= ?
            """,
            (amount, user_id, amount),
        )
        return affected == 1

    async def move_to_bank(self, user_id: int, amount: int) -> tuple[int, int]:
        """Wallet → Bank. `(wallet, bank)` шинэ утгыг буцаана."""
        if not await self.spend_wallet(user_id, amount):
            return -1, -1
        bank = await self.credit_bank(user_id, amount)
        user = await self._require(user_id)
        return user.wallet, bank

    async def move_to_wallet(self, user_id: int, amount: int) -> tuple[int, int]:
        """Bank → Wallet. `(wallet, bank)` шинэ утгыг буцаана."""
        if not await self.spend_bank(user_id, amount):
            return -1, -1
        wallet = await self.credit_wallet(user_id, amount)
        user = await self._require(user_id)
        return wallet, user.bank

    async def set_shield_until(self, user_id: int, until: str | None) -> None:
        await self.db.execute(
            "UPDATE users SET shield_until = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ?",
            (until, user_id),
        )

    # ── XP / Level ─────────────────────────────────────────────────────
    async def add_xp(self, user_id: int, amount: int) -> int:
        if amount < 0:
            raise ValueError("amount >= 0 байх ёстой")
        value = await self.db.fetchval_write(
            """
            UPDATE users
               SET xp = xp + ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ?
            RETURNING xp
            """,
            (amount, user_id),
        )
        if value is None:
            raise UserNotFoundError()
        return int(value)

    async def set_level_xp(self, user_id: int, level: int, xp: int) -> None:
        if level < 1 or xp < 0:
            raise ValueError("level >= 1, xp >= 0 байх ёстой")
        await self.db.execute(
            "UPDATE users SET level = ?, xp = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ?",
            (level, xp, user_id),
        )

    async def add_casino_net(self, user_id: int, delta: int) -> int:
        value = await self.db.fetchval_write(
            """
            UPDATE users
               SET casino_net = casino_net + ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ?
            RETURNING casino_net
            """,
            (delta, user_id),
        )
        if value is None:
            raise UserNotFoundError()
        return int(value)

    async def set_daily(self, user_id: int, streak: int, last_daily_at: str) -> None:
        if streak < 0:
            raise ValueError("streak >= 0 байх ёстой")
        await self.db.execute(
            "UPDATE users SET daily_streak = ?, last_daily_at = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (streak, last_daily_at, user_id),
        )

    # ── Jail ───────────────────────────────────────────────────────────
    async def set_jail(self, user_id: int, *, until: str, bail_cost: int) -> None:
        if bail_cost < 0:
            raise ValueError("bail_cost >= 0 байх ёстой")
        await self.db.execute(
            "UPDATE users SET jail_until = ?, jail_bail_cost = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (until, bail_cost, user_id),
        )

    async def clear_jail(self, user_id: int) -> None:
        await self.db.execute(
            "UPDATE users SET jail_until = NULL, jail_bail_cost = 0, "
            "updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (user_id,),
        )

    # ── Profile ────────────────────────────────────────────────────────
    async def set_title(self, user_id: int, title: str) -> None:
        await self.db.execute(
            "UPDATE users SET active_title = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE user_id = ?",
            (title[:64], user_id),
        )

    async def set_bio(self, user_id: int, bio: str) -> None:
        await self.db.execute(
            "UPDATE users SET bio = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (bio[:300], user_id),
        )

    # ── Skill Point ────────────────────────────────────────────────────
    async def spend_skill_points(self, user_id: int, amount: int) -> bool:
        """Атомик шалгалт + хасалт. Хангалтгүй бол False."""
        if amount <= 0:
            raise ValueError("amount > 0 байх ёстой")
        affected = await self.db.execute(
            """
            UPDATE users
               SET skill_points = skill_points - ?,
                   updated_at   = CURRENT_TIMESTAMP
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
            "UPDATE users SET skill_points = skill_points + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?",
            (amount, user_id),
        )
        return int(
            await self.db.fetchval(
                "SELECT skill_points FROM users WHERE user_id = ?", (user_id,), 0
            )
        )
