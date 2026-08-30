"""𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 — Website backend API (FastAPI).

Firebase дээрх static сайтад зориулсан бяцхан API сервис.
Бот Supabase-д бичдэг (heartbeat, levels, giveaways) → энэ сервис
тухайн өгөгдлийг уншиж сайт руу CORS-оор өгдөг.

Endpoints:
    GET /                 — health
    GET /api/status       — бот online/offline + uptime
    GET /api/leaderboard  — XP топ жагсаалт (?guild_id=&limit=)
    GET /api/giveaways    — giveaway жагсаалт (?guild_id=&active=1)
    GET /api/commands     — командын каталог (?cat=&q=)

Deploy (Railway): backend/Dockerfile эсвэл Root Directory=backend.
Env: SUPABASE_URL, SUPABASE_KEY, ALLOWED_ORIGINS (optional), PORT.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from db import cache_get, cache_set, fetch_rows, is_configured

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("aether.backend")

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
# Бот унтарсан эсэхийг last_ping-ийн шинэ байдлаар шүүх босго (секунд).
# config.js дээрх HEARTBEAT_TIMEOUT_MS=120000-тэй ижил.
HEARTBEAT_FRESH_SECS = int(os.getenv("HEARTBEAT_FRESH_SECS", "120"))

# Cache TTL (секунд) — Supabase дарамтыг бууруулах.
STATUS_CACHE_TTL = float(os.getenv("STATUS_CACHE_TTL", "20"))
LIST_CACHE_TTL = float(os.getenv("LIST_CACHE_TTL", "60"))

DEFAULT_ORIGINS = [
    "https://aether-c1915.web.app",
    "https://aether-c1915.firebaseapp.com",
    "http://localhost",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
_extra = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
ALLOWED_ORIGINS = list(dict.fromkeys(DEFAULT_ORIGINS + _extra))

COMMANDS_PATH = Path(__file__).parent / "data" / "commands.json"

app = FastAPI(
    title="AETHER Backend API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _parse_ts(value: Optional[str]) -> Optional[datetime]:
    """Supabase timestamptz ('2026-08-31T01:23:45.123456+00:00' г.м.) парс."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------
@app.get("/")
@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "service": "aether-backend",
        "db_configured": is_configured(),
        "time": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/status")
async def bot_status() -> Dict[str, Any]:
    """Ботын online/offline төлөв + uptime.

    Эх үүсвэр: Supabase `bot_status` (id=1) — бот 60с тутам ping бичдэг.
    `last_ping` HEARTBEAT_FRESH_SECS-ийн дотор бол online гэж үзнэ.
    """
    if not is_configured():
        raise HTTPException(status_code=503, detail="database_not_configured")

    cached = cache_get("status", STATUS_CACHE_TTL)
    if cached is not None:
        return cached

    try:
        rows = await fetch_rows("bot_status", {"id": "eq.1", "select": "*"})
    except (httpx.HTTPError, RuntimeError) as e:
        log.warning("status fetch failed: %s", e)
        raise HTTPException(status_code=502, detail="supabase_unreachable")

    now = datetime.now(timezone.utc)
    row = rows[0] if rows else {}
    last_ping = _parse_ts(row.get("last_ping"))
    uptime_since = _parse_ts(row.get("uptime_since"))
    age_secs = (now - last_ping).total_seconds() if last_ping else None
    online = bool(last_ping and age_secs is not None and age_secs <= HEARTBEAT_FRESH_SECS)
    uptime_secs = (now - uptime_since).total_seconds() if (online and uptime_since) else 0

    result: Dict[str, Any] = {
        "ok": True,
        "online": online,
        "status": row.get("status") or "unknown",
        "last_ping": row.get("last_ping"),
        "last_ping_age_secs": round(age_secs) if age_secs is not None else None,
        "uptime_secs": round(uptime_secs),
    }
    cache_set("status", result, STATUS_CACHE_TTL)
    return result



@app.get("/api/leaderboard")
async def leaderboard(
    guild_id: str = Query(..., min_length=1, description="Discord guild (server) ID"),
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """XP топ жагсаалт — `levels` хүснэгтээс."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="database_not_configured")

    cache_key = f"lb:{guild_id}:{limit}"
    cached = cache_get(cache_key, LIST_CACHE_TTL)
    if cached is not None:
        return cached

    try:
        rows = await fetch_rows("levels", {
            "guild_id": f"eq.{guild_id}",
            "select": "user_id,xp,level,message_count,voice_seconds",
            "order": "xp.desc",
            "limit": str(limit),
        })
    except (httpx.HTTPError, RuntimeError) as e:
        log.warning("leaderboard fetch failed: %s", e)
        raise HTTPException(status_code=502, detail="supabase_unreachable")

    result = {
        "ok": True,
        "guild_id": guild_id,
        "entries": [
            {"rank": i + 1, **r} for i, r in enumerate(rows)
        ],
    }
    cache_set(cache_key, result, LIST_CACHE_TTL)
    return result


@app.get("/api/giveaways")
async def giveaways(
    guild_id: Optional[str] = Query(None, description="Discord guild ID (заавал биш)"),
    active: bool = Query(False, description="true бол зөвхөн дуусаагүй giveaway"),
) -> Dict[str, Any]:
    """Giveaway жагсаалт — `giveaways` хүснэгтээс."""
    if not is_configured():
        raise HTTPException(status_code=503, detail="database_not_configured")

    cache_key = f"gw:{guild_id}:{active}"
    cached = cache_get(cache_key, LIST_CACHE_TTL)
    if cached is not None:
        return cached

    params: Dict[str, str] = {
        "select": "id,guild_id,channel_id,message_id,prize,winner_count,end_time,ended",
        "order": "end_time.desc",
        "limit": "50",
    }
    if guild_id:
        params["guild_id"] = f"eq.{guild_id}"
    if active:
        params["ended"] = "eq.false"

    try:
        rows = await fetch_rows("giveaways", params)
    except (httpx.HTTPError, RuntimeError) as e:
        log.warning("giveaways fetch failed: %s", e)
        raise HTTPException(status_code=502, detail="supabase_unreachable")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    for r in rows:
        r["is_live"] = (not r.get("ended")) and (r.get("end_time") or 0) > now_ts

    result = {"ok": True, "giveaways": rows}
    cache_set(cache_key, result, LIST_CACHE_TTL)
    return result


@app.get("/api/commands")
async def commands(
    cat: Optional[str] = Query(None, description="Ангилал (Economy, Leveling, ...)"),
    q: Optional[str] = Query(None, description="Нэр/тайлбараар хайх"),
) -> Dict[str, Any]:
    """Командын каталог — data/commands.json (website/js/commands.js-ээс generated)."""
    if not COMMANDS_PATH.exists():
        raise HTTPException(status_code=404, detail="commands.json байхгүй.")

    cached = cache_get("commands_all", 3600)
    if cached is None:
        try:
            cached = json.loads(COMMANDS_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            log.error("commands.json уншигдсангүй: %s", e)
            raise HTTPException(status_code=500, detail="commands_parse_error")
        cache_set("commands_all", cached, 3600)

    items: List[Dict[str, Any]] = cached
    if cat:
        items = [c for c in items if c.get("cat", "").lower() == cat.lower()]
    if q:
        needle = q.lower()
        items = [
            c for c in items
            if needle in c.get("name", "").lower()
            or needle in c.get("desc", "").lower()
            or needle in c.get("descEN", "").lower()
        ]

    cats = sorted({c.get("cat", "Other") for c in cached})
    return {"ok": True, "total": len(items), "categories": cats, "commands": items}
