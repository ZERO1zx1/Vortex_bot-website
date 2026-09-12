"""Supabase REST (PostgREST) async client + TTL cache.

Discord-аас хараат бус — backend зөвхөн Supabase-ийн REST API-г
httpx-ээр дууддаг тул ботын process-той огт холбоогүй, тусдаа
deploy хийгдэх боломжтой.
"""

from __future__ import annotations

import logging
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from redis.asyncio import Redis

log = logging.getLogger("aether.backend.db")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# PostgREST timeout (s). Supabase free tier заримдаа удааширдаг тул
# ботын 30s-тай ижил утга.
REQUEST_TIMEOUT = 30.0

# In-memory TTL cache — Supabase-г хэт их дуудахгүйн тулд.
_cache: Dict[str, Any] = {}
REDIS_URL = os.getenv("REDIS_URL", "")
_redis: Optional[Redis] = Redis.from_url(REDIS_URL, decode_responses=True) if REDIS_URL else None


async def cache_get(key: str, ttl: float) -> Optional[Any]:
    if _redis is not None:
        try:
            raw = await _redis.get(f"aether:{key}")
            return json.loads(raw) if raw is not None else None
        except Exception as exc:  # cache failure must not take down the API
            log.warning("redis cache read failed: %s", exc)
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return value


async def cache_set(key: str, value: Any, ttl: float) -> None:
    if _redis is not None:
        try:
            await _redis.set(f"aether:{key}", json.dumps(value), ex=max(1, int(ttl)))
            return
        except Exception as exc:
            log.warning("redis cache write failed: %s", exc)
    _cache[key] = (value, time.monotonic() + ttl)


def cache_backend() -> str:
    return "redis" if _redis is not None else "memory"


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_KEY)


def _headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Accept": "application/json",
    }


async def fetch_rows(
    table: str,
    params: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """PostgREST-ээс мөрүүд унших. Алдаа гарвал exception шиднэ —
    endpoint талдаа барьж 503/502 болгож хариулна."""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY тохируулагдаагүй.")
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(url, headers=_headers(), params=params or {})
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []
