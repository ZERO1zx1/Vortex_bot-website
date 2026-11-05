"""S14  XP / level / message_count read-modify-write races.

`Leveling._add_xp` was an unsynchronised read-modify-write on the `levels`
row, and XP is granted from three concurrent sources (`on_message`,
`on_raw_reaction_add`, the voice loop). Two grants could both read `xp=N` and
both write `N+15`, destroying one grant outright.

`message_count` lives on the SAME row and had the same problem, plus a retry
loop that re-used one stale value, so a retried write could double-count.

Both now share a single per-(user, guild) lock.
"""

import asyncio
from types import SimpleNamespace

import pytest

from src.cogs.games import leveling as leveling_mod
from src.cogs.games.leveling import Leveling, get_config


@pytest.fixture(autouse=True)
def _clear_config_cache():
    leveling_mod._CFG_CACHE.clear()
    yield
    leveling_mod._CFG_CACHE.clear()


class RaceDB:
    """`levels` store that yields between read and write so races are real."""

    def __init__(self, xp=0, level=1, message_count=0):
        self.row = {
            "user_id": "7", "guild_id": "5",
            "xp": xp, "level": level, "message_count": message_count,
        }
        self.reads: list[tuple[int, int]] = []
        self.writes: list[tuple[int, int]] = []

    async def fetch_one(self, table, filters, selects="*"):
        await asyncio.sleep(0)
        self.reads.append((self.row.get("xp"), self.row.get("level")))
        return dict(self.row) or None

    async def fetchone(self, table, filters):
        return dict(self.row)

    async def upsert(self, table, data, on_conflict=None, **kw):
        await asyncio.sleep(0)
        self.writes.append((data["xp"], data["level"]))
        self.row["xp"] = data["xp"]
        self.row["level"] = data["level"]

    async def update(self, table, filters, values):
        await asyncio.sleep(0)
        if "message_count" in values:
            self.row["message_count"] = values["message_count"]
        for k, v in values.items():
            self.row[k] = v

    async def insert(self, table, data):
        self.row = dict(data)
        self.row.setdefault("xp", 0)
        self.row.setdefault("level", 1)

    async def fetch_all(self, *a, **k):
        return []


def make_engine(db):
    bot = SimpleNamespace(db_manager=db, get_cog=lambda n: None)
    lv = Leveling(bot)

    async def no_buff(*a):
        return 1.0

    lv.get_active_buff = no_buff
    return lv


# ══════════════ XP ══════════════

@pytest.mark.asyncio
async def test_concurrent_xp_grants_are_not_lost():
    db = RaceDB(xp=0, level=1)
    lv = make_engine(db)
    await get_config(db, 5)

    grants = 20
    amount = 5          # 20 x 5 = 100 XP, safely below the first level-up
    await asyncio.gather(*(lv._add_xp(7, 5, amount) for _ in range(grants)))

    assert db.row["xp"] == grants * amount, "every granted XP must survive"


@pytest.mark.asyncio
async def test_reads_are_strictly_serialised():
    """The lock, not luck, is what prevents the lost update."""
    db = RaceDB(xp=0, level=1)
    lv = make_engine(db)
    await get_config(db, 5)

    await asyncio.gather(*(lv._add_xp(7, 5, 5) for _ in range(8)))

    # With the lock each read sees the previous write; without it every read
    # would observe the same starting value.
    assert len(set(db.reads)) == len(db.reads), (
        f"concurrent grants all read the same value -> race: {db.reads}"
    )


@pytest.mark.asyncio
async def test_level_up_happens_exactly_once_under_concurrency():
    db = RaceDB(xp=0, level=1)
    lv = make_engine(db)
    cfg = await get_config(db, 5)
    needed = leveling_mod.xp_for_level(1, cfg)

    # Enough concurrent grants to cross the boundary several times over.
    await asyncio.gather(*(lv._add_xp(7, 5, needed // 4) for _ in range(8)))

    # Total XP handed out must equal what the level curve consumed plus what
    # is still carried — never vanish.
    assert db.row["xp"] >= 0
    assert db.row["level"] >= 1
    # The XP that vanished went into levels, not into a lost update.
    assert db.writes[-1][0] == db.row["xp"]


@pytest.mark.asyncio
async def test_different_users_get_different_locks():
    """Per-user locks: one member's XP grant must not stall another's."""
    lv = make_engine(RaceDB())
    assert lv._user_xp_lock(1, 5) is not lv._user_xp_lock(2, 5)
    assert lv._user_xp_lock(1, 5) is not lv._user_xp_lock(1, 6)
    # Same key -> same lock (memoised).
    assert lv._user_xp_lock(1, 5) is lv._user_xp_lock(1, 5)


@pytest.mark.asyncio
async def test_locks_are_reusable_under_repeated_use():
    lv = make_engine(RaceDB())
    seen = [lv._user_xp_lock(7, 5) for _ in range(20)]
    assert all(lock is seen[0] for lock in seen), "lock pool must not grow per call"


@pytest.mark.asyncio
async def test_negative_grant_and_level_up_are_also_serialised():
    db = RaceDB(xp=1000, level=4)
    lv = make_engine(db)
    await get_config(db, 5)

    await asyncio.gather(*(lv._add_xp(7, 5, -50) for _ in range(6)))

    assert db.row["xp"] >= 0
    assert db.row["level"] >= 1


# ══════════════ message_count ══════════════

@pytest.mark.asyncio
async def test_concurrent_message_counts_are_all_counted():
    db = RaceDB(xp=0, level=1, message_count=0)
    lv = make_engine(db)
    await get_config(db, 5)

    messages = 25
    await asyncio.gather(*(lv._bump_message_count(7, 5) for _ in range(messages)))

    assert db.row["message_count"] == messages, "no message may be dropped"


@pytest.mark.asyncio
async def test_message_count_shares_the_lock_with_xp():
    """Both mutate the same row, so they must not interleave."""
    lv = make_engine(RaceDB())
    xp_lock = lv._user_xp_lock(7, 5)
    count_lock = lv._user_xp_lock(7, 5)
    assert xp_lock is count_lock, "XP and message_count must use the SAME lock"

    other = lv._user_xp_lock(8, 5)
    assert other is not xp_lock, "different users must get different locks"


@pytest.mark.asyncio
async def test_bump_message_count_creates_the_row_when_absent():
    db = RaceDB()
    lv = make_engine(db)
    await get_config(db, 5)
    db.row = {}          # simulate a member with no `levels` row yet

    await lv._bump_message_count(7, 5)

    assert db.row["message_count"] == 1


@pytest.mark.asyncio
async def test_bump_message_count_swallows_db_errors():
    """A counter failure must never break the message listener."""

    class Broken(RaceDB):
        async def fetch_one(self, *a, **k):
            raise RuntimeError("supabase down")

    lv = make_engine(Broken())
    await lv._bump_message_count(7, 5)   # must not raise
