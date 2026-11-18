from __future__ import annotations

import pytest

from core.database import Database
from repositories.user_repo import UserRepository


async def test_grant_skill_points_rejects_negative(db: Database) -> None:
    repo = UserRepository(db)
    with pytest.raises(ValueError, match="amount"):
        await repo.grant_skill_points(1, -1)


async def test_get_many_chunks_large_sets(db: Database) -> None:
    await db.executemany(
        "INSERT INTO users (user_id, wallet) VALUES (?, 500)",
        [(user_id,) for user_id in range(1, 1201)],
    )
    repo = UserRepository(db)
    rows = await repo.get_many([*range(1, 1201), 1, 2])
    assert len(rows) == 1200
    assert rows[1].wallet == 500
    assert rows[1200].wallet == 500


async def test_spend_skill_points_is_atomic(db: Database) -> None:
    await db.execute(
        "INSERT INTO users (user_id, wallet, skill_points) VALUES (1, 500, 2)"
    )
    repo = UserRepository(db)
    assert await repo.spend_skill_points(1, 3) is False
    assert await repo.spend_skill_points(1, 2) is True
    assert await db.fetchval("SELECT skill_points FROM users WHERE user_id = 1") == 0
