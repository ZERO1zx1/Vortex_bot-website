"""Supabase REST (PostgREST) async client + TTL cache.

Discord-аас хараат бус — backend зөвхөн Supabase-ийн REST API-г
httpx-ээр дууддаг тул ботын process-той огт холбоогүй, тусдаа
deploy хийгдэх боломжтой.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger("aether.backend.db")

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

# PostgREST timeout (s). Supabase free tier заримдаа удааширдаг тул
# ботын 30s-тай ижил утга.
REQUEST_TIMEOUT = 30.0

# In-memory TTL cache — Supabase-г хэт их дуудахгүйн тулд.
_cache: Dict[str, Any] = {}


def cache_get(key: str, ttl: float) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    value, expires_at = entry
    if time.monotonic() > expires_at:
        _cache.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any, ttl: float) -> None:
    _cache[key] = (value, time.monotonic() + ttl)


def is_configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _headers() -> Dict[str, str]:
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Accept": "application/json",
    }


async def fetch_rows(
    table: str,
    params: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """PostgREST-ээс мөрүүд унших. Алдаа гарвал exception шиднэ —
    endpoint талдаа барьж 503/502 болгож хариулна."""
    if not is_configured():
        raise RuntimeError("SUPABASE_URL / SUPABASE_KEY тохируулагдаагүй.")
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        resp = await client.get(url, headers=_headers(), params=params or {})
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else []
