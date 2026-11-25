"""`guild_settings` хүснэгтийн Data Access Layer.

Cog болон bot.py шууд SQL бичихгүй — prefix/tax/log channel бүгд эндээс.
"""

from __future__ import annotations

from dataclasses import dataclass

import config
from core.database import Database, Row


@dataclass(frozen=True, slots=True)
class GuildSettingsRow:
    guild_id: int
    prefix: str
    tax_pct: float
    log_channel_id: int | None
    created_at: str
    updated_at: str

    @classmethod
    def from_row(cls, row: Row) -> GuildSettingsRow:
        return cls(
            guild_id=row["guild_id"],
            prefix=row["prefix"],
            tax_pct=row["tax_pct"],
            log_channel_id=row["log_channel_id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


_SELECT = """
    SELECT guild_id, prefix, tax_pct, log_channel_id, created_at, updated_at
      FROM guild_settings
"""


class GuildRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get(self, guild_id: int) -> GuildSettingsRow | None:
        row = await self.db.fetchone(f"{_SELECT} WHERE guild_id = ?", (guild_id,))
        return GuildSettingsRow.from_row(row) if row else None

    async def get_or_create(self, guild_id: int) -> GuildSettingsRow:
        await self.db.execute(
            "INSERT INTO guild_settings (guild_id, prefix) VALUES (?, ?) "
            "ON CONFLICT (guild_id) DO NOTHING",
            (guild_id, config.DEFAULT_PREFIX),
        )
        row = await self.db.fetchone(f"{_SELECT} WHERE guild_id = ?", (guild_id,))
        if row is None:
            raise RuntimeError(f"guild_settings мөр үүсгэж чадсангүй: {guild_id}")
        return GuildSettingsRow.from_row(row)

    async def prefix(self, guild_id: int | None) -> str:
        if guild_id is None:
            return config.DEFAULT_PREFIX
        row = await self.get(guild_id)
        return row.prefix if row else config.DEFAULT_PREFIX

    async def set_prefix(self, guild_id: int, prefix: str) -> None:
        prefix = prefix.strip()
        if not 1 <= len(prefix) <= 5 or any(ch.isspace() for ch in prefix):
            raise ValueError("prefix нь зайгүй, 1–5 тэмдэгт байх ёстой")
        await self.db.execute(
            """
            INSERT INTO guild_settings (guild_id, prefix)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                prefix = excluded.prefix,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, prefix),
        )

    async def set_tax(self, guild_id: int, tax_pct: float) -> None:
        if not 0.0 <= tax_pct <= 0.5:
            raise ValueError("tax_pct 0.0–0.5 байх ёстой")
        await self.db.execute(
            """
            INSERT INTO guild_settings (guild_id, tax_pct)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                tax_pct = excluded.tax_pct,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, tax_pct),
        )

    async def set_log_channel(self, guild_id: int, channel_id: int | None) -> None:
        await self.db.execute(
            """
            INSERT INTO guild_settings (guild_id, log_channel_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id) DO UPDATE SET
                log_channel_id = excluded.log_channel_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (guild_id, channel_id),
        )

    async def tax_pct(self, guild_id: int | None) -> float:
        if guild_id is None:
            return 0.0
        row = await self.get(guild_id)
        return row.tax_pct if row else 0.0
