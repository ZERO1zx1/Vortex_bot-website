"""Async, TTL-bounded configuration cache shared by high-frequency cogs.

Guild configs (counting, confessions, greetings, avatar logging, invites,
temporary voice, ...) are read on every relevant event.  Before this cache,
each cog re-fetched them from Supabase per event, so a transient DB problem
was re-discovered hundreds of times.

Design:

* TTL per entry (default 20s).
* Explicit ``invalidate`` for config writes so changes apply immediately.
* One ``asyncio.Lock`` per key so concurrent readers coalesce into a single
  DB fetch (no stampede).
* Bounded memory — an ``OrderedDict`` capped by maxsize evicts LRU entries.

Values are plain Python objects (the caller's hydrated config), so no
serialization is needed.  Empty/Falsy results (e.g. ``None`` from
``fetch_safe``) are deliberately cacheable so an unconfigured guild does not
hammer the DB on every message.
"""

import asyncio
import logging
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from typing import Generic, TypeVar
from weakref import WeakValueDictionary

T = TypeVar("T")

logger = logging.getLogger("aether.config_cache")

class ConfigCache(Generic[T]):
    def __init__(self, ttl: float = 20.0, maxsize: int = 512, name: str = "config"):
        if maxsize < 1:
            raise ValueError("maxsize must be positive")
        self._ttl = ttl
        self._maxsize = maxsize
        self._name = name
        self._entries: OrderedDict[str, tuple[float, T]] = OrderedDict()
        # Active callers keep their lock alive. Completed keys do not leak
        # locks, and LRU eviction cannot split one key's in-flight waiters.
        self._locks: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()
        self._loads: dict[str, object] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _peek(self, key: str) -> tuple[bool, T]:
        """Return ``(present, value)`` — ``present=False`` when absent/expired."""
        item = self._entries.get(key)
        if item is None:
            return False, None
        expire_at, value = item
        if self._now() >= expire_at:
            self._entries.pop(key, None)
            return False, None
        self._entries.move_to_end(key)
        return True, value

    def invalidate(self, key: object) -> None:
        k = str(key)
        self._entries.pop(k, None)
        self._loads.pop(k, None)

    def clear(self) -> None:
        self._entries.clear()
        self._loads.clear()

    def get_cached(self, key: object) -> T | None:
        """Synchronous lookup (no DB fetch). ``None`` for a genuinely cached
        ``None`` value is indistinguishable from a miss here; use
        :meth:`get` when that distinction matters."""
        present, value = self._peek(str(key))
        return value if present else None

    async def get(
        self,
        key: object,
        loader: Callable[[], Awaitable[T]],
    ) -> T:
        """Return the cached value or load it with ``loader`` (exactly once
        per key across concurrent callers)."""
        k = str(key)
        present, value = self._peek(k)
        if present:
            return value

        lock = self._locks.get(k)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[k] = lock
        async with lock:
            # double-check: another coroutine may have filled it while waiting
            present, value = self._peek(k)
            if present:
                return value
            token = object()
            self._loads[k] = token
            try:
                value = await loader()
                # A write may invalidate while the read awaits the DB. Never
                # let that stale read resurrect the invalidated cache entry.
                if self._loads.get(k) is token:
                    self._store(k, value)
                return value
            finally:
                if self._loads.get(k) is token:
                    self._loads.pop(k, None)

    def _store(self, key: str, value: T) -> None:
        self._entries[key] = (self._now() + self._ttl, value)
        self._entries.move_to_end(key)
        # Bound memory: evict oldest entries beyond maxsize.
        while len(self._entries) > self._maxsize:
            self._entries.popitem(last=False)


def cached_config(
    cache: ConfigCache[T],
    key: object,
    loader: Callable[[], Awaitable[T]],
):
    """Small convenience so cogs can write ``cfg = await cached_config(...)``."""
    return cache.get(key, loader)
