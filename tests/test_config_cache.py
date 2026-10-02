import asyncio
import gc

import pytest

from src.utils.config_cache import ConfigCache


@pytest.mark.asyncio
async def test_loads_once_and_caches():
    cache = ConfigCache(ttl=60.0, name="test")

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return {"value": calls}

    assert await cache.get("key", loader) == {"value": 1}
    assert await cache.get("key", loader) == {"value": 1}
    assert calls == 1


@pytest.mark.asyncio
async def test_concurrent_loaders_coalesce_into_one_fetch():
    cache = ConfigCache(ttl=60.0, name="test")

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)  # widen the race window
        return {"call": calls}

    results = await asyncio.gather(
        cache.get("shared", loader),
        cache.get("shared", loader),
        cache.get("shared", loader),
    )
    assert results == [{"call": 1}, {"call": 1}, {"call": 1}]
    assert calls == 1


@pytest.mark.asyncio
async def test_invalidate_forces_reload():
    cache = ConfigCache(ttl=60.0, name="test")

    async def loader():
        return "v1"

    assert await cache.get("k", loader) == "v1"
    cache.invalidate("k")
    async def loader2():
        return "v2"
    assert await cache.get("k", loader2) == "v2"


@pytest.mark.asyncio
async def test_ttl_expiry_reloads():
    cache = ConfigCache(ttl=0.01, name="test")

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1
        return calls

    assert await cache.get("k", loader) == 1
    await asyncio.sleep(0.02)
    assert await cache.get("k", loader) == 2
    assert calls == 2


@pytest.mark.asyncio
async def test_falsy_values_are_cacheable():
    """None configuration (unconfigured guild) must not pump the DB forever."""
    cache = ConfigCache(ttl=60.0, name="test")

    calls = 0

    async def loader():
        nonlocal calls
        calls += 1

    assert await cache.get("k", loader) is None
    assert await cache.get("k", loader) is None
    assert calls == 1


@pytest.mark.asyncio
async def test_bounded_size_evicts_lru():
    cache = ConfigCache(ttl=60.0, maxsize=2, name="test")
    async def loader(v):
        return v

    await cache.get("a", lambda: loader("a"))
    await cache.get("b", lambda: loader("b"))
    await cache.get("c", lambda: loader("c"))
    assert cache.get_cached("a") is None  # evicted
    assert cache.get_cached("b") is not None
    assert cache.get_cached("c") is not None


@pytest.mark.asyncio
async def test_loader_exception_propagates_but_does_not_cache():
    cache = ConfigCache(ttl=60.0, name="test")

    async def loader():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cache.get("k", loader)
    assert cache.get_cached("k") is None


@pytest.mark.asyncio
async def test_completed_loads_release_locks_when_entries_are_evicted():
    cache = ConfigCache(ttl=60.0, maxsize=2, name="bounded-locks")

    async def loader():
        return "loaded"

    for key in range(100):
        assert await cache.get(key, loader) == "loaded"

    gc.collect()
    assert len(cache._entries) == 2
    assert len(cache._locks) == 0
    assert len(cache._loads) == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("invalidate_all", [False, True])
async def test_invalidation_during_load_does_not_recache_stale_value(invalidate_all):
    cache = ConfigCache(ttl=60.0, name="inflight-invalidation")
    started = asyncio.Event()
    release = asyncio.Event()

    async def stale_loader():
        started.set()
        await release.wait()
        return "before-write"

    task = asyncio.create_task(cache.get("guild", stale_loader))
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        if invalidate_all:
            cache.clear()
        else:
            cache.invalidate("guild")
        release.set()
        assert await asyncio.wait_for(task, timeout=1) == "before-write"
    finally:
        if not task.done():
            task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    assert cache.get_cached("guild") is None
    assert len(cache._loads) == 0

    async def fresh_loader():
        return "after-write"

    assert await cache.get("guild", fresh_loader) == "after-write"
