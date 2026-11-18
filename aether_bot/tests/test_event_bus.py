from __future__ import annotations

import asyncio

from core.database import Database
from core.event_bus import EventBus, XPGained


async def test_handler_failure_does_not_break_others() -> None:
    bus = EventBus()
    calls: list[int] = []

    async def good(event: XPGained) -> None:
        calls.append(event.user_id)

    async def bad(event: XPGained) -> None:
        raise RuntimeError("boom")

    bus.subscribe(XPGained, good)
    bus.subscribe(XPGained, bad)
    assert await bus.publish(XPGained(user_id=7, amount=1, source="test")) == 1
    assert calls == [7]


async def test_emit_does_not_share_parent_transaction(db: Database) -> None:
    bus = EventBus()
    started = asyncio.Event()
    done = asyncio.Event()
    errors: list[RuntimeError] = []
    observed: list[bool] = []

    @bus.on(XPGained)
    async def handler(event: XPGained) -> None:
        observed.append(db.in_transaction())
        started.set()
        try:
            await db.execute("INSERT INTO users (user_id, wallet) VALUES (1, 500)")
        except RuntimeError as exc:
            errors.append(exc)
        done.set()

    async with db.transaction():
        await bus.emit(XPGained(user_id=1, amount=1, source="test"))
        await asyncio.wait_for(started.wait(), timeout=1.0)
        await asyncio.sleep(0.05)

    await asyncio.wait_for(done.wait(), timeout=1.0)
    assert observed == [False]
    assert errors == []
    assert await db.fetchval("SELECT COUNT(*) FROM users WHERE user_id = 1") == 1
