from __future__ import annotations

import random
from typing import Any

import pytest

from core.database import Database
from core.exceptions import (
    GameStateError,
    InsufficientFundsError,
    InvalidBetError,
    ValidationError,
)
from repositories.log_repo import LogRepository
from repositories.skill_repo import SkillRepository
from repositories.user_repo import UserRepository
from services.casino.blackjack_service import BlackjackService
from services.casino.coinflip_service import CoinflipService
from services.casino.crash_service import CrashService, crash_point_from_roll
from services.casino.lottery_service import LotteryService
from services.casino.minefield_service import MinefieldService
from services.casino.roulette_service import RouletteService
from services.casino.slots_service import SlotsService
from services.rpg.skill_service import SkillService


class StubRng(random.Random):
    """Тестэд зориулсан детерминик RNG."""

    def __init__(
        self,
        *,
        random_value: float = 0.5,
        int_value: int = 10,
        choice_value: Any = None,
        choices_values: list[Any] | None = None,
        sample_values: list[int] | None = None,
        uniform_value: float = 0.5,
    ) -> None:
        super().__init__()
        self.random_value = random_value
        self.int_value = int_value
        self.choice_value = choice_value
        self.choices_values = choices_values
        self.sample_values = sample_values
        self.uniform_value = uniform_value

    def random(self) -> float:
        return self.random_value

    def randint(self, low: int, high: int) -> int:
        return max(low, min(high, self.int_value))

    def choice(self, seq: Any) -> Any:
        if self.choice_value is not None:
            return self.choice_value
        return seq[0]

    def choices(  # type: ignore[override]
        self, population: Any, **kwargs: Any
    ) -> list[Any]:
        if self.choices_values is not None:
            return list(self.choices_values)
        return [population[0]]

    def sample(  # type: ignore[override]
        self, population: Any, k: int
    ) -> list[int]:
        if self.sample_values is not None:
            return list(self.sample_values)[:k]
        return list(population)[:k]

    def uniform(self, low: float, high: float) -> float:
        return max(low, min(high, self.uniform_value))

    def shuffle(self, deck: list[Any]) -> None:  # type: ignore[override]
        return None


async def test_coinflip_win_and_loss(db: Database) -> None:
    users = UserRepository(db)
    win = CoinflipService(db, users=users, rng=StubRng(choice_value="heads"))
    result = await win.flip(1, 100, "heads")
    assert result.payout == 192
    assert result.net == 92
    assert result.wallet == 592
    assert result.outcome == "win"
    assert (await LogRepository(db).recent_casino(1))[0].game == "coinflip"

    loss = CoinflipService(db, users=users, rng=StubRng(choice_value="tails"))
    result = await loss.flip(1, 100, "heads")
    assert result.payout == 0
    assert result.cashback == 0
    assert result.net == -100
    assert result.wallet == 492
    assert result.outcome == "loss"


async def test_coinflip_validates_choice_bet_and_balance(db: Database) -> None:
    service = CoinflipService(db, rng=StubRng())
    with pytest.raises(ValidationError):
        await service.flip(1, 100, "banana")
    with pytest.raises(InvalidBetError):
        await service.flip(1, 10, "heads")
    with pytest.raises(InsufficientFundsError):
        await service.flip(1, 10_000, "heads")


async def test_lucky_star_cashback_on_loss(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    skills_repo = SkillRepository(db)
    for _ in range(5):
        await skills_repo.increment_level(1, "lucky_star", 5)
    skills = SkillService(db, user_repo=users)
    service = CoinflipService(
        db, users=users, skills=skills, rng=StubRng(choice_value="tails")
    )
    result = await service.flip(1, 100, "heads")
    assert result.payout == 0
    assert result.cashback == 10  # 5 түвшин × 2%
    assert result.net == -90
    assert result.wallet == 410
    history = await LogRepository(db).recent_casino(1)
    assert history[0].payout == 0


async def test_slots_winning_lines_and_house_edge(db: Database) -> None:
    all_cherries = ["🍒"] * 9
    service = SlotsService(db, rng=StubRng(choices_values=all_cherries))
    result = await service.spin(1, 100)
    assert len(result.detail["lines"]) == 5
    assert result.detail["raw_win"] == 1_000  # 5 шугам × 2 × 100
    assert result.payout == 960
    assert result.wallet == 1_360

    no_lines = ["🍒", "🔔", "💎", "🍒", "🔔", "💎", "🍒", "🔔", "💎"]
    service = SlotsService(db, rng=StubRng(choices_values=no_lines))
    result = await service.spin(1, 100)
    assert result.payout == 0
    assert result.detail["lines"] == []
    assert result.wallet == 1_260


async def test_roulette_even_money_and_number(db: Database) -> None:
    service = RouletteService(db, rng=StubRng(int_value=7))
    result = await service.play(1, 100, "red")
    assert result.payout == 192
    assert result.detail["landed"] == 7
    assert result.detail["color"] == "red"
    assert result.wallet == 592

    result = await service.play(1, 100, "black")
    assert result.payout == 0
    assert result.wallet == 492

    result = await service.play(1, 100, "number", 7)
    assert result.payout == 3_456  # 100 × 36 × 0.96
    assert result.wallet == 3_848

    with pytest.raises(ValidationError):
        await service.play(1, 100, "number", 37)
    with pytest.raises(ValidationError):
        await service.play(1, 100, "banana")


async def test_roulette_zero_loses_even_money(db: Database) -> None:
    service = RouletteService(db, rng=StubRng(int_value=0))
    result = await service.play(1, 50, "red")
    assert result.payout == 0
    assert result.detail["color"] == "green"


async def test_minefield_reveal_cashout_and_bomb(db: Database) -> None:
    service = MinefieldService(db, rng=StubRng(sample_values=[0, 1, 2, 3]))
    state = await service.start(1, 100, mines=4)
    assert state.active is True
    assert state.bet == 100

    state = await service.reveal(1, state.game_id, 4)
    assert state.active is True
    assert state.multiplier == pytest.approx(1.28)
    state = await service.reveal(1, state.game_id, 5)
    assert state.multiplier == pytest.approx(1.7455, abs=1e-3)

    state = await service.cashout(1, state.game_id)
    assert state.active is False
    assert state.outcome == "cashout"
    assert state.payout == 174
    assert state.wallet == 574

    with pytest.raises(GameStateError):
        await service.reveal(1, state.game_id, 6)


async def test_minefield_bomb_ends_game(db: Database) -> None:
    service = MinefieldService(db, rng=StubRng(sample_values=[0, 1, 2, 3]))
    state = await service.start(1, 100, mines=4)
    state = await service.reveal(1, state.game_id, 0)
    assert state.active is False
    assert state.outcome == "loss"
    assert state.payout == 0
    assert 0 in state.bombs
    assert state.wallet == 400


async def test_minefield_auto_cashout_and_guard(db: Database) -> None:
    service = MinefieldService(db, rng=StubRng(sample_values=[15, 14, 13, 12]))
    with pytest.raises(ValidationError):
        await service.start(1, 100, mines=20)
    state = await service.start(1, 100, mines=4)
    with pytest.raises(ValidationError):
        await service.reveal(1, state.game_id, 99)
    for tile in [index for index in range(16) if index not in {12, 13, 14, 15}]:
        state = await service.reveal(1, state.game_id, tile)
        if not state.active:
            break
    assert state.active is False
    assert state.outcome == "auto_cashout"
    assert state.payout > 0


def test_crash_point_distribution_bounds() -> None:
    assert crash_point_from_roll(0.0) == 1.0
    assert crash_point_from_roll(0.5) == pytest.approx(2.0)
    assert crash_point_from_roll(1.0) <= 20.0


async def test_crash_cashout_and_bust(db: Database) -> None:
    service = CrashService(db, rng=StubRng(random_value=0.5))
    state = await service.start(1, 100)
    assert state.active is True
    state = await service.cashout(1, state.game_id, elapsed_sec=4.0)
    assert state.outcome == "cashout"
    assert state.multiplier == pytest.approx(1.8)
    assert state.payout == 172
    assert state.wallet == 572

    state = await service.start(2, 100)
    state = await service.cashout(2, state.game_id, elapsed_sec=6.0)
    assert state.outcome == "bust"
    assert state.payout == 0
    assert state.wallet == 400


class RiggedBlackjack(BlackjackService):
    """`_new_deck`-ийг тогтмол дараалалтай картаар солино."""

    def __init__(self, *args: Any, deck: list[str], **kwargs: Any) -> None:
        self._test_deck = deck
        super().__init__(*args, **kwargs)

    def _new_deck(self) -> list[str]:
        return list(self._test_deck)


async def test_blackjack_win_and_push(db: Database) -> None:
    # pop дараалал: player 10, dealer 9, player 9, dealer 8 → player 19, dealer 17
    service = RiggedBlackjack(db, deck=["8♣", "9♦", "9♥", "10♠"])
    state = await service.start(1, 100)
    assert state.status == "active"
    assert state.player_total == 19
    assert state.dealer_total is None
    state = await service.stand(1, state.game_id)
    assert state.outcome == "win"
    assert state.payout == 196
    assert state.wallet == 596

    # player 10+7, dealer 10+7 → push
    service = RiggedBlackjack(db, deck=["7♣", "10♦", "7♥", "10♠"])
    state = await service.start(2, 100)
    state = await service.stand(2, state.game_id)
    assert state.outcome == "push"
    assert state.payout == 100
    assert state.wallet == 500


async def test_blackjack_bust_double_and_natural(db: Database) -> None:
    # player 10+7, hit 9 → 26 bust
    service = RiggedBlackjack(db, deck=["9♣", "8♦", "7♥", "9♠", "10♠"])
    state = await service.start(1, 100)
    state = await service.hit(1, state.game_id)
    assert state.outcome == "loss"
    assert state.payout == 0
    assert state.wallet == 400

    # player 10+7, double 4 → 21; dealer 17 → 2×bet win
    service = RiggedBlackjack(db, deck=["4♣", "8♦", "9♥", "7♣", "10♠"])
    state = await service.start(2, 100)
    state = await service.double(2, state.game_id)
    assert state.doubled is True
    assert state.bet == 200
    assert state.outcome == "win"
    assert state.payout == 392
    assert state.wallet == 692

    # natural blackjack 3:2
    service = RiggedBlackjack(db, deck=["8♣", "9♦", "10♥", "A♠"])
    state = await service.start(3, 100)
    assert state.outcome == "win"
    assert state.payout == 244
    assert state.wallet == 644


async def test_blackjack_wrong_turn_is_blocked(db: Database) -> None:
    service = RiggedBlackjack(db, deck=["8♣", "9♦", "7♥", "9♠", "10♠"])
    state = await service.start(1, 100)
    with pytest.raises(GameStateError):
        await service.hit(2, state.game_id)


async def test_lottery_buy_and_draw(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    service = LotteryService(db, users=users, rng=StubRng(choice_value=2))

    info = await service.buy(1, 2)
    assert info.round_id == 1
    assert info.tickets == 2
    assert info.pot == 500
    info = await service.buy(2, 1)
    assert info.tickets == 3
    assert info.pot == 750
    assert await service.my_tickets(1) == 2

    draw = await service.draw()
    assert draw.round_id == 1
    assert draw.winner_id == 2
    assert draw.tickets == 3
    assert draw.pot == 750
    assert draw.payout == 720
    assert (await users.get(1)).wallet == 0  # type: ignore[union-attr]
    assert (await users.get(2)).wallet == 970  # type: ignore[union-attr]
    assert (await service.info()).tickets == 0
    assert (await service.current_round()) == 2
    with pytest.raises(ValidationError):
        await service.draw()


async def test_lottery_limits_and_balance(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.credit_wallet(1, 10_000)
    service = LotteryService(db, users=users)
    await service.buy(1, 20)
    with pytest.raises(ValidationError, match="дээд тал нь"):
        await service.buy(1, 1)
    with pytest.raises(ValidationError):
        await service.buy(1, 0)
    with pytest.raises(InsufficientFundsError):
        await service.buy(2, 5)


async def test_lottery_repository_ticket_counts(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    service = LotteryService(db, users=users)
    await service.buy(1, 2)
    info = await service.info()
    assert info.participants[0].tickets == 2
