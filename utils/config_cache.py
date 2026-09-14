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
from typing import Awaitable, Callable, Dict, Generic, Optional, Tuple, TypeVar

T = TypeVar("T")

logger = logging.getLogger("aether.config_cache")

_MISSING = object()


class ConfigCache(Generic[T]):
    def __init__(self, ttl: float = 20.0, maxsize: int = 512, name: str = "config"):
        self._ttl = ttl
        self._maxsize = maxsize
        self._name = name
        self._entries: "OrderedDict[str, Tuple[float, T]]" = OrderedDict()
        self._mutex = asyncio.Lock()
        self._locks: Dict[str, asyncio.Lock] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _peek(self, key: str) -> Tuple[bool, T]:
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
        self._entries.pop(str(key), None)

    def clear(self) -> None:
        self._entries.clear()

    def get_cached(self, key: object) -> Optional[T]:
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
            value = await loader()
            self._store(k, value)
            return value

    def _store(self, key: str, value: T) -> None:
        self._entries[key] = (self._now() + self._ttl, value)
        self._entries.move_to_end(key)
        # Bound memory: evict oldest entries beyond maxsize.
        while len(self._entries) > self._maxsize:
            _, (old_key, __) = self._entries.popitem(last=False)
            # Bound lock memory too: drop the evicted key's lock so the
            # `_locks` dict cannot grow without limit.
            self._locks.pop(old_key, None)


def cached_config(
    cache: ConfigCache[T],
    key: object,
    loader: Callable[[], Awaitable[T]],
):
    """Small convenience so cogs can write ``cfg = await cached_config(...)``."""
    return cache.get(key, loader)