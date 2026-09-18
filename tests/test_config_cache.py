import asyncio

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
        return None

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