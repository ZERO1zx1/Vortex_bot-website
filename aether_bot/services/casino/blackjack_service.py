"""Blackjack — Hit / Stand / Double state machine.

Дүрэм:
- Dealer 17 хүртэл татна, 17 ба түүнээс дээш зогсоно.
- Blackjack (эхний 2 карт 21) нь 3:2 төлнө (4% edge-тэй).
- Push үед бооцоо бүрэн буцаана.
- Double нь зөвхөн эхний 2 карттай үед, нэмэлт бооцоо тавьж нэг карт татна.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from core.exceptions import GameStateError, ValidationError
from core.locks import user_lock
from services.casino.base import CasinoResult, CasinoService

SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")


def card_value(card: str) -> int:
    rank = card[:-1]
    if rank == "A":
        return 11
    if rank in {"J", "Q", "K"}:
        return 10
    return int(rank)


def hand_total(cards: list[str]) -> int:
    total = sum(card_value(card) for card in cards)
    aces = sum(1 for card in cards if card[:-1] == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def is_blackjack(cards: list[str]) -> bool:
    return len(cards) == 2 and hand_total(cards) == 21


@dataclass(slots=True)
class _Game:
    game_id: str
    user_id: int
    bet: int
    deck: list[str]
    player: list[str] = field(default_factory=list)
    dealer: list[str] = field(default_factory=list)
    doubled: bool = False
    active: bool = True

    def draw(self) -> str:
        if not self.deck:
            raise GameStateError("✦ Картын багц дууссан байна.")
        return self.deck.pop()


def _fresh_deck() -> list[str]:
    return [f"{rank}{suit}" for suit in SUITS for rank in RANKS]


@dataclass(frozen=True, slots=True)
class BlackjackState:
    game_id: str
    bet: int
    player_cards: tuple[str, ...]
    player_total: int
    dealer_cards: tuple[str, ...]
    dealer_total: int | None
    status: str  # active | done
    doubled: bool = False
    payout: int = 0
    cashback: int = 0
    net: int = 0
    wallet: int = 0
    outcome: str = "active"
    xp: int = 0


class BlackjackService(CasinoService):
    game = "blackjack"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._games: dict[str, _Game] = {}

    def _new_deck(self) -> list[str]:
        deck = _fresh_deck() * 6
        self.rng.shuffle(deck)
        return deck

    def _require_game(self, user_id: int, game_id: str) -> _Game:
        game = self._games.get(game_id)
        if game is None or game.user_id != user_id or not game.active:
            raise GameStateError()
        return game

    def _state(self, game: _Game) -> BlackjackState:
        done = not game.active
        dealer_cards = tuple(game.dealer) if done else (game.dealer[0],)
        player_total = hand_total(game.player)
        return BlackjackState(
            game_id=game.game_id,
            bet=game.bet,
            player_cards=tuple(game.player),
            player_total=player_total,
            dealer_cards=dealer_cards,
            dealer_total=hand_total(game.dealer) if done else None,
            status="done" if done else "active",
            doubled=game.doubled,
        )

    def _finished_state(self, game: _Game, result: CasinoResult) -> BlackjackState:
        return BlackjackState(
            game_id=game.game_id,
            bet=game.bet,
            player_cards=tuple(game.player),
            player_total=hand_total(game.player),
            dealer_cards=tuple(game.dealer),
            dealer_total=hand_total(game.dealer),
            status="done",
            doubled=game.doubled,
            payout=result.payout,
            cashback=result.cashback,
            net=result.net,
            wallet=result.wallet,
            outcome=result.outcome,
            xp=result.xp,
        )

    async def start(self, user_id: int, raw_bet: str | int) -> BlackjackState:
        if any(game.user_id == user_id for game in self._games.values()):
            raise GameStateError("✦ Танд нээлттэй blackjack тоглоом байна.")

        finished: CasinoResult | None = None
        async with user_lock(user_id), self.db.transaction():
            bet = await self._prepare(user_id, raw_bet)
            await self._lock(user_id, bet)
            game = _Game(
                game_id=secrets.token_hex(4),
                user_id=user_id,
                bet=bet,
                deck=self._new_deck(),
            )
            game.player = [game.draw(), game.draw()]
            game.dealer = [game.draw(), game.draw()]

            if is_blackjack(game.player) and is_blackjack(game.dealer):
                finished = await self._settle_game(game, "push", bet)
            elif is_blackjack(game.player):
                profit = int(game.bet * 1.5)
                payout = game.bet + self.with_edge(profit)
                finished = await self._settle_game(game, "blackjack", payout)
            elif is_blackjack(game.dealer):
                finished = await self._settle_game(game, "loss", 0)
            else:
                self._games[game.game_id] = game

        if finished is not None:
            await self._award_xp(user_id, finished.xp)
            return self._finished_state(game, finished)
        return self._state(game)

    async def hit(self, user_id: int, game_id: str) -> BlackjackState:
        game = self._require_game(user_id, game_id)
        finished: CasinoResult | None = None
        async with user_lock(user_id), self.db.transaction():
            game.player.append(game.draw())
            total = hand_total(game.player)
            if total > 21:
                finished = await self._settle_game(game, "bust", 0)
            elif total == 21:
                finished = await self._stand_locked(game)
        if finished is not None:
            await self._award_xp(user_id, finished.xp)
            return self._finished_state(game, finished)
        return self._state(game)

    async def stand(self, user_id: int, game_id: str) -> BlackjackState:
        game = self._require_game(user_id, game_id)
        async with user_lock(user_id), self.db.transaction():
            result = await self._stand_locked(game)
        await self._award_xp(user_id, result.xp)
        return self._finished_state(game, result)

    async def double(self, user_id: int, game_id: str) -> BlackjackState:
        game = self._require_game(user_id, game_id)
        if len(game.player) != 2:
            raise ValidationError("✦ Double зөвхөн эхний 2 карттай үед боломжтой.")
        finished: CasinoResult | None = None
        async with user_lock(user_id), self.db.transaction():
            bet = await self._prepare(user_id, game.bet)
            await self._lock(user_id, bet)
            game.bet += bet
            game.doubled = True
            game.player.append(game.draw())
            if hand_total(game.player) > 21:
                finished = await self._settle_game(game, "bust", 0)
            else:
                finished = await self._stand_locked(game)
        if finished is not None:
            await self._award_xp(user_id, finished.xp)
            return self._finished_state(game, finished)
        return self._state(game)

    async def _stand_locked(self, game: _Game) -> CasinoResult:
        while hand_total(game.dealer) < 17:
            game.dealer.append(game.draw())
        player = hand_total(game.player)
        dealer = hand_total(game.dealer)
        if dealer > 21 or player > dealer:
            payout = game.bet + self.with_edge(game.bet)
            return await self._settle_game(game, "win", payout)
        if player == dealer:
            return await self._settle_game(game, "push", game.bet)
        return await self._settle_game(game, "loss", 0)

    async def _settle_game(
        self, game: _Game, outcome: str, payout: int
    ) -> CasinoResult:
        game.active = False
        self._games.pop(game.game_id, None)
        detail = {
            "player": list(game.player),
            "dealer": list(game.dealer),
            "player_total": hand_total(game.player),
            "dealer_total": hand_total(game.dealer),
            "doubled": game.doubled,
            "result": outcome,
        }
        log_outcome = {"blackjack": "win", "bust": "loss"}.get(outcome, outcome)
        xp = 4 if payout > 0 else 2
        return await self._finish(
            game.user_id, game.bet, payout, log_outcome, detail, xp=xp
        )
