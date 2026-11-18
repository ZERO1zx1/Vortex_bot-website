"""Discord API-ийн глобал rate limiter (45 req/s).

Discord-ийн хязгаар: 50 HTTP request / секунд (global). Бид 45 дээр
ажилласнаар 429 (Too Many Requests) болон 5 секундын global ban-аас
сэргийлнэ. Мөн route бүрд жижиг bucket хөтөлж, нэг командаас үүдэлтэй
товчны шуурга (burst) саатуулна.

Discord обьектыг шууд import хийхгүй — duck typing ашигласнаар энэ модуль
тестлэхэд хялбар, discord.py хувилбараас хамааралгүй.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from typing import Any

log = logging.getLogger(__name__)


class RateLimiter:
    """Sliding-window (token bucket-ийн тэгш хувилбар) лимитер.

    `acquire()` нь цонхонд багтах зай гартал хүлээнэ. Async, тиймээс
    бүх корутин нэг event loop-д шударгаар дараалалд орно (FIFO).
    """

    def __init__(
        self,
        max_rate: int = 45,
        per_seconds: float = 1.0,
        *,
        burst: int | None = None,
    ) -> None:
        if max_rate <= 0:
            raise ValueError("max_rate > 0 байх ёстой")
        if per_seconds <= 0:
            raise ValueError("per_seconds > 0 байх ёстой")
        if burst is not None and burst < 1:
            raise ValueError("burst >= 1 байх ёстой")
        self.max_rate = max_rate
        self.per_seconds = float(per_seconds)
        # Цонхны хэмжээ; burst өгөөгүй бол лимиттэй тэнцүү
        self.capacity = burst if burst is not None else max_rate
        self._events: deque[float] = deque()
        self._lock = asyncio.Lock()
        self._total = 0
        self._delays = 0

    async def acquire(self, amount: int = 1) -> None:
        """`amount` ширхэг request-ийн зайг эзэлнэ (шаардлагатай бол хүлээнэ)."""
        amount = max(1, amount)
        if amount > self.capacity:
            raise ValueError(f"amount <= capacity ({self.capacity}) байх ёстой")
        while True:
            async with self._lock:
                now = time.monotonic()
                self._trim(now)
                if len(self._events) + amount <= self.capacity:
                    for _ in range(amount):
                        self._events.append(time.monotonic())
                    self._total += amount
                    return
                # Хамгийн эртний event цонхноос гарах хүртэл хүлээнэ
                wait = self.per_seconds - (now - self._events[0])
                if len(self._events) + amount > self.capacity and wait <= 0:
                    wait = 0.01
            self._delays += 1
            await asyncio.sleep(max(wait, 0.005) + 0.002)

    def _trim(self, now: float) -> None:
        horizon = now - self.per_seconds
        while self._events and self._events[0] <= horizon:
            self._events.popleft()

    # ── Хяналт ─────────────────────────────────────────────────────────
    @property
    def used_in_window(self) -> int:
        self._trim(time.monotonic())
        return len(self._events)

    def stats(self) -> dict[str, Any]:
        return {
            "limit": f"{self.max_rate}/{self.per_seconds:g}s",
            "used_in_window": self.used_in_window,
            "total_requests": self._total,
            "delays_applied": self._delays,
        }


class RouteLimiter:
    """Route бүрийн нэмэлт bucket (жишээ нь нэг суваг руу message burst).

    Discord route-ууд өөрсдийн bucket-тэй байдаг ч, бидний хариу үйлдэл
    олон мессеж илгээхэд 429 болохоос энэ нь хамгаална.
    """

    def __init__(self, per_route: int = 5, per_seconds: float = 2.0) -> None:
        self.per_route = per_route
        self.per_seconds = per_seconds
        self._buckets: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, route: str) -> None:
        key = route or "unknown"
        while True:
            async with self._lock:
                now = time.monotonic()
                bucket = self._buckets.setdefault(key, deque())
                horizon = now - self.per_seconds
                while bucket and bucket[0] <= horizon:
                    bucket.popleft()
                if len(bucket) < self.per_route:
                    bucket.append(now)
                    return
                wait = self.per_seconds - (now - bucket[0])
            await asyncio.sleep(max(wait, 0.01))


def install_http_guard(
    bot: Any,
    *,
    max_rate: int = 45,
    per_seconds: float = 1.0,
) -> dict[str, Any]:
    """`bot.http.request`-ийг лимитерээр ороож, хэрэглэгдэж буй limiter-уудыг буцаана.

    Ботыг `setup_hook()` дотор, `login()`-оос өмнө дуудна::

        limiters = install_http_guard(bot, max_rate=config.RATE_LIMIT_PER_SECOND)

    Discord.py-ийн дотоод дуудлагууд бүгд `HTTPClient.request`-ээр явдаг тул
    энэ нь глобал хамгаалалт болно. (Модуль import хийхгүй, duck typing.)
    """
    http = getattr(bot, "http", None)
    if http is None:
        raise RuntimeError("bot.http олдсонгүй — discord.Client бус обьект байна.")

    limiter = RateLimiter(max_rate=max_rate, per_seconds=per_seconds)
    routes = RouteLimiter()
    original = http.request

    async def rate_limited_request(*args: Any, **kwargs: Any) -> Any:
        # `route` эхний positional arg (discord.py: request(route, method, ...))
        route = args[0] if args else kwargs.get("route", "unknown")
        await routes.acquire(str(route))
        await limiter.acquire()
        return await original(*args, **kwargs)

    http.request = rate_limited_request
    log.info(
        "HTTP rate limit суулгагдлаа: %s req / %ss (route bucket %s / %ss)",
        max_rate,
        per_seconds,
        routes.per_route,
        routes.per_seconds,
    )
    return {"limiter": limiter, "routes": routes}


# Бот ачаалахаас өмнөх аюулгүй default (импорт хийхэд л бэлэн)
global_limiter = RateLimiter(max_rate=45)
