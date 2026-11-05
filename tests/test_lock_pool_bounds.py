"""S16  Lock pools must not grow without bound.

`Economy._balance_locks`, `ShopCog._inventory_locks`, `Leveling._xp_locks` and
`Tickets._open_locks` each gained one entry per (user, guild[, item]) pair
ever seen and never released them. They now hold weak references, following
the pattern already used by `level_admin._CONFIG_LOCKS`.

A weak value is safe here because every caller holds the lock for the whole
critical section (`async with self._lock(...)`), so the object is referenced
exactly as long as it can still be contended.
"""

import asyncio
import gc
from types import SimpleNamespace

import pytest

from src.cogs.community.tickets import Tickets
from src.cogs.economy.economy import Economy
from src.cogs.games.leveling import Leveling
from src.cogs.shop.shop import ShopCog


def _pools():
    econ = Economy.__init__
    return [
        ("Economy._balance_locks", econ),
        ("ShopCog._inventory_locks", ShopCog.__init__),
        ("Leveling._xp_locks", Leveling.__init__),
        ("Tickets._open_locks", Tickets.__init__),
    ]


@pytest.mark.parametrize("name,init", _pools())
def test_lock_pool_is_weak(name, init):
    src = __import__("inspect").getsource(init)
    assert "WeakValueDictionary" in src, f"{name} must hold weak references"


@pytest.mark.asyncio
async def test_idle_locks_are_reclaimed():
    cog = Leveling(SimpleNamespace(db_manager=None, get_cog=lambda n: None))
    for uid in range(200):
        lock = cog._user_xp_lock(uid, 5)
        assert lock is not None
    # Drop every local reference, then let the collector run.
    gc.collect()
    assert len(cog._xp_locks) < 200, (
        f"pool kept {len(cog._xp_locks)}/200 idle locks"
    )


@pytest.mark.asyncio
async def test_a_live_lock_is_not_reclaimed_mid_critical_section():
    cog = Leveling(SimpleNamespace(db_manager=None, get_cog=lambda n: None))
    held = []

    async def worker():
        async with cog._user_xp_lock(7, 5):
            held.append(cog._user_xp_lock(7, 5))
            gc.collect()
            await asyncio.sleep(0.02)
            # Still the same object: it must not have been swapped mid-section.
            assert cog._user_xp_lock(7, 5) is held[0]

    await asyncio.gather(worker(), worker(), worker())
    assert held and held[0] is not None


@pytest.mark.asyncio
async def test_contended_section_is_actually_serialized():
    cog = Tickets(SimpleNamespace(db_manager=None, get_cog=lambda n: None))
    order = []

    async def worker(n):
        async with cog._open_lock(5, 7):
            order.append(("in", n))
            await asyncio.sleep(0.01)
            order.append(("out", n))

    await asyncio.gather(*(worker(i) for i in range(4)))

    # Strict alternation proves mutual exclusion.
    assert len(order) == 8
    for i in range(0, 8, 2):
        assert order[i][0] == "in"
        assert order[i + 1][0] == "out"
        assert order[i][1] == order[i + 1][1]


@pytest.mark.asyncio
async def test_different_keys_do_not_serialize_each_other():
    cog = Tickets(SimpleNamespace(db_manager=None, get_cog=lambda n: None))
    first_entered = asyncio.Event()
    second_entered = asyncio.Event()

    async def hold(key, entered):
        async with cog._open_lock(5, key):
            entered.set()
            await asyncio.sleep(0.05)

    t1 = asyncio.create_task(hold(1, first_entered))
    await first_entered.wait()
    t2 = asyncio.create_task(hold(2, second_entered))
    await asyncio.wait_for(second_entered.wait(), timeout=0.2)
    await asyncio.gather(t1, t2)