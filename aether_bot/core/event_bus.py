"""Async EventBus — модулиудын хоорондын сул холболт (loose coupling).

Жишээ: `/work` ажилласны дараа `EconomyService` `XPGained` event нийтэлнэ.
`LevelService` түүнийг сонсож XP нэмнэ, `LevelUp` болвол `SkillService`
SP олгоно, quest систем ахина. Энд ямар ч service нөгөөгөө шууд дуудахгүй.

Дүрэм:
- Handler-ийн алдаа нэг event-ийн бусад handler-ийг унагахгүй (логдоно).
- `publish` нь бүх handler дууссаны дараа буцна (await).
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from utils.time_utils import utcnow

log = logging.getLogger(__name__)

Handler = Callable[[Any], Awaitable[None]]


# ── Event төрлүүд ─────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True, kw_only=True)
class Event:
    """Бүх event-ийн суурь. `Event`-д харьяалагдсан handler бүгдийг сонсоно."""

    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True, slots=True, kw_only=True)
class XPGained(Event):
    user_id: int
    amount: int
    source: str  # 'chat' | 'work' | 'daily' | 'casino' | 'duel' | 'adventure'
    multiplier: float = 1.0


@dataclass(frozen=True, slots=True, kw_only=True)
class LevelUp(Event):
    user_id: int
    previous_level: int
    new_level: int
    skill_points_awarded: int
    coins_awarded: int


@dataclass(frozen=True, slots=True, kw_only=True)
class MoneyChanged(Event):
    user_id: int
    amount: int  # + орлого / - зарлага
    source: str
    wallet_after: int
    bank_after: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillUpgraded(Event):
    user_id: int
    skill_id: str
    previous_level: int
    new_level: int
    skill_points_left: int


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillActivated(Event):
    user_id: int
    skill_id: str
    active_until: datetime
    cooldown_sec: int


@dataclass(frozen=True, slots=True, kw_only=True)
class CasinoResolved(Event):
    user_id: int
    game: str
    bet: int
    payout: int
    outcome: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserJailed(Event):
    user_id: int
    until: datetime
    bail_cost: int
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserReleased(Event):
    user_id: int
    reason: str  # bail | expired


@dataclass(frozen=True, slots=True, kw_only=True)
class QuestProgress(Event):
    user_id: int
    quest_key: str
    increment: int = 1


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[type[Event], list[Handler]] = defaultdict(list)
        # Fire-and-forget task-уудыг GC-ээс хамгаалж, дууссаны дараа цэвэрлэнэ.
        self._background: set[asyncio.Task[Any]] = set()

    # ── Бүртгэл ────────────────────────────────────────────────────────
    def subscribe(self, event_type: type[Event], handler: Handler) -> None:
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: type[Event], handler: Handler) -> None:
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def on(self, event_type: type[Event]) -> Callable[[Handler], Handler]:
        """Decorator: `@bus.on(XPGained)`"""

        def decorator(handler: Handler) -> Handler:
            self.subscribe(event_type, handler)
            return handler

        return decorator

    # ── Нийтлэх ────────────────────────────────────────────────────────
    def _handlers_for(self, event: Event) -> list[Handler]:
        matched: list[Handler] = []
        for cls in type(event).__mro__:
            if not issubclass(cls, Event):
                continue
            for handler in self._handlers.get(cls, ()):  # type: ignore[arg-type]
                if handler not in matched:
                    matched.append(handler)
        return matched

    async def publish(self, event: Event) -> int:
        """Бүх тохирох handler-ийг зэрэг ажиллуулж, амжилттай тоог буцаана."""
        handlers = self._handlers_for(event)
        if not handlers:
            return 0

        results = await asyncio.gather(
            *(self._safe_call(h, event) for h in handlers), return_exceptions=True
        )
        failures = sum(1 for r in results if r is not True)
        return len(handlers) - failures

    async def _safe_call(self, handler: Handler, event: Event) -> bool:
        try:
            await handler(event)
            return True
        except Exception:  # event bus нэг handler-ээр уначихгүй
            log.exception(
                "Event handler алдаа: %s ← %s",
                getattr(handler, "__qualname__", handler),
                type(event).__name__,
            )
            return False

    async def emit(self, event: Event) -> None:
        """`publish`-ийн await-гүй хувилбар: handler-уудыг task болгож салгана.

        Хоосон context-оор эхлүүлнэ — ингэснээр emit-ийг транзакц дотор
        дуудсан ч handler нь эцэг task-ийн SQLite холболтыг санамсаргүй
        өвлөхгүй. Event-ийг commit-ийн дараа нийтлэх нь зөв хэвээр.
        """
        for handler in self._handlers_for(event):
            task = asyncio.create_task(
                self._safe_call(handler, event), context=contextvars.Context()
            )
            self._background.add(task)
            task.add_done_callback(self._background.discard)


# Бот дотор ганц instance: `bot.event_bus`
bus = EventBus()
