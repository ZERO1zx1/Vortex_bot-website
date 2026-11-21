"""Minefield — 4×4 талбай, бөмбөгөөс зайлсхийж Cashout хийх.

Тоглогч бөмбөггүй tile-уудыг нээх тусам үржүүлэгч өснө. Бөмбөг дээр
дарвал бооцоо алдагдаж, Lucky Star cashback тооцогдоно. Бүх аюулгүй
tile-ийг нээвэл автоматаар cashout болно.
"""

from __future__ import annotations

import math
import secrets
from dataclasses import dataclass, field
from typing import Any

import config
from core.exceptions import GameStateError, ValidationError
from core.locks import user_lock
from services.casino.base import CasinoResult, CasinoService

TILES = 16


@dataclass(slots=True)
class _Game:
    game_id: str
    user_id: int
    bet: int
    mines: set[int]
    revealed: set[int] = field(default_factory=set)


@dataclass(frozen=True, slots=True)
class MinefieldState:
    game_id: str
    bet: int
    revealed: tuple[int, ...]
    multiplier: float
    active: bool
    mines_total: int
    bombs: tuple[int, ...] = ()
    payout: int = 0
    cashback: int = 0
    net: int = 0
    wallet: int = 0
    outcome: str = "active"
    xp: int = 0


def fair_multiplier(mines: int, revealed: int) -> float:
    if revealed <= 0:
        return 1.0
    safe = TILES - mines
    if revealed > safe:
        return 0.0
    return math.comb(TILES, revealed) / math.comb(safe, revealed)


class MinefieldService(CasinoService):
    game = "minefield"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._games: dict[str, _Game] = {}

    def _require_game(self, user_id: int, game_id: str) -> _Game:
        game = self._games.get(game_id)
        if game is None or game.user_id != user_id:
            raise GameStateError()
        return game

    def _state(self, game: _Game) -> MinefieldState:
        multiplier = max(
            1.0,
            fair_multiplier(len(game.mines), len(game.revealed))
            * (1.0 - config.CASINO_HOUSE_EDGE),
        )
        return MinefieldState(
            game_id=game.game_id,
            bet=game.bet,
            revealed=tuple(sorted(game.revealed)),
            multiplier=round(multiplier, 4),
            active=True,
            mines_total=len(game.mines),
        )

    async def start(
        self, user_id: int, raw_bet: str | int, mines: int = 4
    ) -> MinefieldState:
        if not 1 <= int(mines) <= 12:
            raise ValidationError("✦ Бөмбөгийн тоо **1–12** хооронд байх ёстой.")
        if any(game.user_id == user_id for game in self._games.values()):
            raise GameStateError("✦ Танд нээлттэй minefield тоглоом байна.")

        async with user_lock(user_id), self.db.transaction():
            bet = await self._prepare(user_id, raw_bet)
            await self._lock(user_id, bet)
            bombs = set(self.rng.sample(range(TILES), int(mines)))
            game = _Game(
                game_id=secrets.token_hex(4),
                user_id=user_id,
                bet=bet,
                mines=bombs,
            )
            self._games[game.game_id] = game
        return self._state(game)

    async def reveal(self, user_id: int, game_id: str, tile: int) -> MinefieldState:
        game = self._require_game(user_id, game_id)
        tile = int(tile)
        if not 0 <= tile < TILES:
            raise ValidationError("✦ Tile нь **0–15** хооронд байх ёстой.")
        if tile in game.revealed:
            raise ValidationError("✦ Энэ tile аль хэдийн нээгдсэн.")

        async with user_lock(user_id), self.db.transaction():
            if tile in game.mines:
                payout = 0
                detail = {
                    "tile": tile,
                    "bombs": sorted(game.mines),
                    "revealed": sorted(game.revealed),
                }
                result = await self._finish(
                    user_id, game.bet, payout, "loss", detail, xp=2
                )
                self._games.pop(game_id, None)
                state = MinefieldState(
                    game_id=game_id,
                    bet=game.bet,
                    revealed=tuple(sorted(game.revealed)),
                    multiplier=0.0,
                    active=False,
                    mines_total=len(game.mines),
                    bombs=tuple(sorted(game.mines)),
                    payout=result.payout,
                    cashback=result.cashback,
                    net=result.net,
                    wallet=result.wallet,
                    outcome="loss",
                    xp=result.xp,
                )
            else:
                game.revealed.add(tile)
                safe = TILES - len(game.mines)
                if len(game.revealed) >= safe:
                    result = await self._cashout_transaction(game, tile=tile)
                    self._games.pop(game_id, None)
                    state = self._state_from_result(game, result, auto=True, tile=tile)
                else:
                    state = self._state(game)

        if not state.active:
            await self._award_xp(user_id, state.xp)
        return state

    async def cashout(self, user_id: int, game_id: str) -> MinefieldState:
        game = self._require_game(user_id, game_id)
        async with user_lock(user_id), self.db.transaction():
            result = await self._cashout_transaction(game)
            self._games.pop(game_id, None)
            state = self._state_from_result(game, result, auto=False)
        await self._award_xp(user_id, state.xp)
        return state

    async def _cashout_transaction(
        self, game: _Game, *, tile: int | None = None
    ) -> CasinoResult:
        multiplier = max(
            1.0,
            fair_multiplier(len(game.mines), len(game.revealed))
            * (1.0 - config.CASINO_HOUSE_EDGE),
        )
        payout = int(game.bet * multiplier)
        detail = {
            "multiplier": round(multiplier, 4),
            "revealed": sorted(game.revealed),
            "bombs": sorted(game.mines),
        }
        if tile is not None:
            detail["auto_tile"] = tile
        return await self._finish(game.user_id, game.bet, payout, "win", detail, xp=4)

    def _state_from_result(
        self,
        game: _Game,
        result: CasinoResult,
        *,
        auto: bool,
        tile: int | None = None,
    ) -> MinefieldState:
        return MinefieldState(
            game_id=game.game_id,
            bet=game.bet,
            revealed=tuple(sorted(game.revealed)),
            multiplier=float(result.detail.get("multiplier", 0.0)),
            active=False,
            mines_total=len(game.mines),
            bombs=tuple(sorted(game.mines)),
            payout=result.payout,
            cashback=result.cashback,
            net=result.net,
            wallet=result.wallet,
            outcome="auto_cashout" if auto else "cashout",
            xp=result.xp,
        )
