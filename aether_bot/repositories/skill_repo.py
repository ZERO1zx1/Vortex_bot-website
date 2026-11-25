"""`user_skills` хүснэгтийн Data Access Layer.

`skill_id` нь TEXT (skill catalog-ийн түлхүүр) — FK байхгүй, учир нь skill
тодорхойлолт нь код дотор (`core/skill_catalog.py`) амьдардаг. Энэ нь
тэнцвэр өөрчлөхөд DB migration шаардахгүй болгоно.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.database import Database, Row


@dataclass(frozen=True, slots=True)
class SkillRow:
    user_id: int
    skill_id: str
    skill_level: int
    last_used_at: str | None
    active_until: str | None

    @classmethod
    def from_row(cls, row: Row) -> SkillRow:
        return cls(
            user_id=row["user_id"],
            skill_id=row["skill_id"],
            skill_level=row["skill_level"],
            last_used_at=row["last_used_at"],
            active_until=row["active_until"],
        )


class SkillRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_all(self, user_id: int) -> dict[str, SkillRow]:
        rows = await self.db.fetchall(
            """
            SELECT user_id, skill_id, skill_level, last_used_at, active_until
              FROM user_skills
             WHERE user_id = ?
            """,
            (user_id,),
        )
        return {row["skill_id"]: SkillRow.from_row(row) for row in rows}

    async def get(self, user_id: int, skill_id: str) -> SkillRow | None:
        row = await self.db.fetchone(
            """
            SELECT user_id, skill_id, skill_level, last_used_at, active_until
              FROM user_skills
             WHERE user_id = ? AND skill_id = ?
            """,
            (user_id, skill_id),
        )
        return SkillRow.from_row(row) if row else None

    async def increment_level(self, user_id: int, skill_id: str, max_level: int) -> int:
        """Түвшинг 1-ээр нэмнэ (дээд хязгаарт хүрээгүй бол). Шинэ түвшинг буцаана.

        Атомик: `WHERE skill_level < max_level` тул зэрэг дарсан ч хязгаар
        хэтрэхгүй.
        """
        await self.db.execute(
            """
            INSERT INTO user_skills (user_id, skill_id, skill_level)
            VALUES (?, ?, 0)
            ON CONFLICT(user_id, skill_id) DO NOTHING
            """,
            (user_id, skill_id),
        )
        await self.db.execute(
            """
            UPDATE user_skills
               SET skill_level = skill_level + 1
             WHERE user_id = ? AND skill_id = ? AND skill_level < ?
            """,
            (user_id, skill_id, max_level),
        )
        return int(
            await self.db.fetchval(
                "SELECT skill_level FROM user_skills WHERE user_id = ? AND skill_id = ?",
                (user_id, skill_id),
                0,
            )
        )

    async def set_activation(
        self,
        user_id: int,
        skill_id: str,
        *,
        last_used_at: str,
        active_until: str | None,
    ) -> None:
        """Active skill-ийн cooldown эхлэл ба эффектийн хугацааг бичнэ."""
        await self.db.execute(
            """
            INSERT INTO user_skills (user_id, skill_id, skill_level, last_used_at, active_until)
            VALUES (?, ?, 0, ?, ?)
            ON CONFLICT(user_id, skill_id) DO UPDATE SET
                last_used_at = excluded.last_used_at,
                active_until = excluded.active_until
            """,
            (user_id, skill_id, last_used_at, active_until),
        )

    async def clear_active(self, user_id: int, skill_id: str) -> None:
        """Цэнэгийг хэрэглэсний дараа `active_until`-ийг цэвэрлэнэ."""
        await self.db.execute(
            "UPDATE user_skills SET active_until = NULL WHERE user_id = ? AND skill_id = ?",
            (user_id, skill_id),
        )

    async def delete_all(self, user_id: int) -> int:
        return await self.db.execute(
            "DELETE FROM user_skills WHERE user_id = ?", (user_id,)
        )

    async def total_spent_points(self, user_id: int) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COALESCE(SUM(skill_level), 0) FROM user_skills WHERE user_id = ?",
                (user_id,),
                0,
            )
        )
