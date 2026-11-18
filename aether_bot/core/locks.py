"""Per-user (болон per-key) asyncio Lock manager.

Яагаад хэрэгтэй вэ: нэг хэрэглэгч хоёр `/casino` эсвэл `/rob`-ыг зэрэг
ажиллуулбал мөнгө давхар суутгах / үржих боломжтой. Тиймээс мөнгө хөдөлгөх
бүх үйлдэл `async with user_lock(user_id):` дор орно.

Lock нь **reentrant**: нэг task дотор `user_lock(1)`-ийг дахин авбал
deadlock болохгүй, зөвхөн depth нэмэгдэнэ. Жишээ нь `ShopService` нь
`user_lock` барьсан хэвээр `SkillService.reset()`-ийг дуудаж болно.

`acquire_many` нь түлхүүрүүдийг эрэмбэлж авдаг тул хоёр тоглогч бие биеэ
хүлээх deadlock үүсэхгүй (`/duel`, `/transfer`).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Hashable
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class _LockEntry:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    owner: asyncio.Task[Any] | None = None
    depth: int = 0
    refs: int = 0


class PerUserLockManager:
    def __init__(self) -> None:
        self._locks: dict[Hashable, _LockEntry] = {}

    def _entry_for(self, key: Hashable) -> _LockEntry:
        entry = self._locks.get(key)
        if entry is None:
            entry = self._locks[key] = _LockEntry()
        return entry

    def _release_ref(self, key: Hashable, entry: _LockEntry) -> None:
        entry.refs -= 1
        # Зөвхөн хүлээж байгаа хэн ч байхгүй үед цэвэрлэнэ.
        if (
            entry.refs <= 0
            and not entry.lock.locked()
            and self._locks.get(key) is entry
        ):
            self._locks.pop(key, None)

    @asynccontextmanager
    async def acquire(self, key: Hashable) -> AsyncIterator[None]:
        entry = self._entry_for(key)
        entry.refs += 1
        current = asyncio.current_task()
        reentrant = current is not None and entry.owner is current

        if reentrant:
            entry.depth += 1
            try:
                yield
            finally:
                entry.depth -= 1
                self._release_ref(key, entry)
            return

        try:
            async with entry.lock:
                entry.owner = current
                entry.depth = 1
                try:
                    yield
                finally:
                    entry.depth = 0
                    entry.owner = None
        finally:
            self._release_ref(key, entry)

    @asynccontextmanager
    async def acquire_many(self, *keys: Hashable) -> AsyncIterator[None]:
        """Олон түлхүүрийг тогтмол эрэмбээр авч deadlock-оос сэргийлнэ."""
        unique = sorted({k for k in keys if k is not None}, key=repr)
        async with AsyncExitStack() as stack:
            for key in unique:
                await stack.enter_async_context(self.acquire(key))
            yield

    def is_locked(self, key: Hashable) -> bool:
        entry = self._locks.get(key)
        return bool(entry and entry.lock.locked())

    def active_keys(self) -> int:
        return len(self._locks)


# Бүх service энэ ганц instance-ийг ашиглана.
user_locks = PerUserLockManager()


def user_lock(key: Hashable):
    """`async with user_lock(user_id): ...`"""
    return user_locks.acquire(key)


def multi_user_lock(*keys: Hashable):
    """`async with multi_user_lock(a, b): ...`"""
    return user_locks.acquire_many(*keys)
