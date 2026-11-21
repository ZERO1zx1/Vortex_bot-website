from __future__ import annotations

import asyncio

from core.locks import user_lock, user_locks


async def test_nested_lock_is_reentrant() -> None:
    async with user_lock(1):
        assert user_locks.is_locked(1)
        async with user_lock(1):
            assert user_locks.is_locked(1)
        assert user_locks.is_locked(1)
    assert not user_locks.is_locked(1)
    assert user_locks.active_keys() == 0


async def test_other_task_waits_until_release() -> None:
    started = asyncio.Event()
    release = asyncio.Event()
    entered = asyncio.Event()

    async def holder() -> None:
        async with user_lock(2):
            started.set()
            await release.wait()

    async def waiter() -> None:
        async with user_lock(2):
            entered.set()

    holder_task = asyncio.create_task(holder())
    waiter_task = asyncio.create_task(waiter())
    await asyncio.wait_for(started.wait(), timeout=1.0)
    await asyncio.sleep(0.05)
    assert not entered.is_set()
    release.set()
    await asyncio.wait_for(asyncio.gather(holder_task, waiter_task), timeout=1.0)
    assert entered.is_set()
    assert user_locks.active_keys() == 0


async def test_multi_lock_deduplicates_keys() -> None:
    async with user_lock(3), user_lock(3):
        assert user_locks.is_locked(3)
    assert user_locks.active_keys() == 0
