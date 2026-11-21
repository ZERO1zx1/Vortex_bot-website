"""Crash — үржүүлэгч өсөх хооронд Cashout хийх.

`start()` нь бооцоог escrow-д авч, далд `crash_point` үүсгэнэ. Үржүүлэгч
цаг хугацаатай өснө (`1.0 + 0.20 × секунд`). Тоглогч `cashout()` дуудах үед
одоогийн үржүүлэгч `crash_point`-оос бага бол хожно, эс бөгөөс бүх бооцоо
алдагдана. Тест болон UI-д зориулж `elapsed_sec`-ийг шууд өгч болно.
"""

from __future__ import annotations

import math
import secrets
import time
from dataclasses import dataclass
from typing import Any

import config
from core.exceptions import GameStateError
from core.locks import user_lock
from services.casino.base import CasinoService

GROWTH_PER_SECOND = 0.20
MAX_CRASH = 20.0


@dataclass(slots=True)
class _Game:
    game_id: str
    user_id: int
    bet: int
    crash_point: float
    started_at: float


@dataclass(frozen=True, slots=True)
class CrashState:
    game_id: str
    bet: int
    multiplier: float
    active: bool
    crash_point: float | None = None
    payout: int = 0
    cashback: int = 0
    net: int = 0
    wallet: int = 0
    outcome: str = "active"
    xp: int = 0


def crash_point_from_roll(roll: float) -> float:
    roll = min(0.999_999, max(0.0, roll))
    return min(MAX_CRASH, max(1.0, 1.0 / (1.0 - roll)))


class CrashService(CasinoService):
    game = "crash"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._games: dict[str, _Game] = {}

    def _require_game(self, user_id: int, game_id: str) -> _Game:
        game = self._games.get(game_id)
        if game is None or game.user_id != user_id:
            raise GameStateError()
        return game

    @staticmethod
    def multiplier_at(game: _Game, elapsed_sec: float) -> float:
        return max(1.0, 1.0 + max(0.0, elapsed_sec) * GROWTH_PER_SECOND)

    async def start(self, user_id: int, raw_bet: str | int) -> CrashState:
        if any(game.user_id == user_id for game in self._games.values()):
            raise GameStateError("✦ Танд нээлттэй crash тоглоом байна.")
        async with user_lock(user_id), self.db.transaction():
            bet = await self._prepare(user_id, raw_bet)
            await self._lock(user_id, bet)
            game = _Game(
                game_id=secrets.token_hex(4),
                user_id=user_id,
                bet=bet,
                crash_point=crash_point_from_roll(self.rng.random()),
                started_at=time.monotonic(),
            )
            self._games[game.game_id] = game
        return CrashState(
            game_id=game.game_id,
            bet=bet,
            multiplier=1.0,
            active=True,
        )

    async def status(self, user_id: int, game_id: str) -> CrashState:
        game = self._require_game(user_id, game_id)
        elapsed = time.monotonic() - game.started_at
        multiplier = self.multiplier_at(game, elapsed)
        return CrashState(
            game_id=game_id,
            bet=game.bet,
            multiplier=round(multiplier, 2),
            active=True,
        )

    async def cashout(
        self,
        user_id: int,
        game_id: str,
        *,
        elapsed_sec: float | None = None,
    ) -> CrashState:
        game = self._require_game(user_id, game_id)
        elapsed = (
            time.monotonic() - game.started_at
            if elapsed_sec is None
            else float(elapsed_sec)
        )
        multiplier = self.multiplier_at(game, elapsed)
        busted = multiplier >= game.crash_point

        async with user_lock(user_id), self.db.transaction():
            if busted:
                detail = {
                    "multiplier": round(multiplier, 4),
                    "crash_point": round(game.crash_point, 4),
                    "elapsed_sec": round(elapsed, 2),
                }
                result = await self._finish(user_id, game.bet, 0, "loss", detail, xp=2)
            else:
                payout = max(
                    0,
                    math.floor(
                        game.bet * multiplier * (1.0 - config.CASINO_HOUSE_EDGE)
                    ),
                )
                detail = {
                    "multiplier": round(multiplier, 4),
                    "crash_point": round(game.crash_point, 4),
                    "elapsed_sec": round(elapsed, 2),
                }
                result = await self._finish(
                    user_id, game.bet, payout, "cashout", detail, xp=4
                )
            self._games.pop(game_id, None)

        await self._award_xp(user_id, result.xp)
        return CrashState(
            game_id=game_id,
            bet=game.bet,
            multiplier=round(multiplier, 2),
            active=False,
            crash_point=round(game.crash_point, 2),
            payout=result.payout,
            cashback=result.cashback,
            net=result.net,
            wallet=result.wallet,
            outcome="bust" if busted else "cashout",
            xp=result.xp,
        )


# `Any`-г typing-д ашиглаж байгаа тул lint-д зориулж экспортолно.
__all__ = ["CrashService", "CrashState", "crash_point_from_roll"]
