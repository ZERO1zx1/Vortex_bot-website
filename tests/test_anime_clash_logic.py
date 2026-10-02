from types import SimpleNamespace

import pytest

import src.cogs.anime_clash as clash_mod
from src.cogs.anime_clash import (
    MAX_ENERGY,
    WIN_REWARD_MAX,
    WIN_REWARD_MIN,
    AnimeClashGame,
    AnimeClashView,
    hp_bar,
)


def make_game():
    return AnimeClashGame(7, enemy=("🌑 Test Ronin", "Test boss"))


def test_new_game_starts_with_full_health():
    game = make_game()

    assert game.player_hp == 115
    assert game.enemy_hp == 100
    assert game.energy == 0
    assert game.finished is False
    assert len(game.game_id) == 12
    assert int(game.game_id, 16) >= 0


def test_win_reward_is_flavor_sized():
    assert (WIN_REWARD_MIN, WIN_REWARD_MAX) == (200, 500)


def test_attack_damages_both_sides_and_builds_energy(monkeypatch):
    game = make_game()
    rolls = iter((20, 15))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    result = game.take_turn("attack")

    assert result["status"] == "continue"
    assert game.enemy_hp == 77
    assert game.player_hp == 100
    assert game.energy == 1


def test_guard_reduces_incoming_damage(monkeypatch):
    game = make_game()
    rolls = iter((5, 20))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    result = game.take_turn("guard")

    assert result["guarded"] is True
    assert result["received"] == 3
    assert game.player_hp == 112
    assert game.energy == 0


def test_focus_trades_damage_for_healing_and_two_energy(monkeypatch):
    game = make_game()
    game.player_hp = 70
    rolls = iter((18, 16))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    result = game.take_turn("focus")

    assert result["dealt"] == 0
    assert result["healed"] == 18
    assert game.player_hp == 72
    assert game.energy == 2


def test_ultimate_requires_full_energy():
    game = make_game()

    result = game.take_turn("skill")

    assert result == {"status": "no_energy"}
    assert game.turn == 0
    assert game.enemy_hp == 100


def test_ultimate_can_finish_battle(monkeypatch):
    game = make_game()
    game.energy = MAX_ENERGY
    game.enemy_hp = 30
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: 40)

    result = game.take_turn("skill")

    assert result["status"] == "win"
    assert game.enemy_hp == 0
    assert game.energy == 0
    assert game.finished is True


def test_hero_and_difficulty_change_stats():
    game = AnimeClashGame(7, enemy=("Boss", "Hard"), hero="mage", difficulty="hard")

    assert game.max_hp == 90
    assert game.enemy_max_hp == 135
    assert game.player_hp == 90
    assert game.enemy_hp == 135


def test_guard_then_attack_activates_counter_combo(monkeypatch):
    game = make_game()
    rolls = iter((3, 12, 16, 12))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    game.take_turn("guard")
    result = game.take_turn("attack")

    assert result["combo_name"] == "COUNTER SLASH"
    assert result["dealt"] == 27
    assert game.best_chain == 2


def test_burn_ticks_on_two_turns_after_ultimate(monkeypatch):
    game = make_game()
    game.energy = MAX_ENERGY
    rolls = iter((35, 12, 16, 12, 16, 12))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    skill = game.take_turn("skill")
    first_tick = game.take_turn("attack")
    second_tick = game.take_turn("attack")

    assert skill["burn_damage"] == 0
    assert first_tick["burn_damage"] == 5
    assert second_tick["burn_damage"] == 5
    assert game.burn_turns == 0


@pytest.mark.parametrize("hero", ["samurai", "mage", "assassin", "healer"])
def test_daily_boss_is_beatable_by_every_class(monkeypatch, hero):
    game = AnimeClashGame(7, enemy=("Daily", "Boss"), hero=hero, difficulty="daily")
    monkeypatch.setattr(clash_mod.random, "randint", lambda low, high: (low + high) // 2)

    for action in ("attack", "focus", "skill", "guard", "attack", "attack"):
        result = game.take_turn(action)
        if game.finished:
            break

    assert result["status"] == "win"
    assert game.player_hp > 0


def test_hp_bar_is_clamped():
    assert hp_bar(100) == "▰" * 10
    assert hp_bar(45) == "▰" * 4 + "▱" * 6
    assert hp_bar(50) == "▰" * 5 + "▱" * 5
    assert hp_bar(55) == "▰" * 5 + "▱" * 5
    assert hp_bar(0) == "▱" * 10
    assert hp_bar(90, 180) == "▰" * 5 + "▱" * 5
    assert hp_bar(99, 100) == "▰" * 9 + "▱"
    assert hp_bar(1, 100) == "▰" + "▱" * 9


@pytest.mark.asyncio
async def test_failed_reward_can_be_retried(monkeypatch):
    class Bank:
        def __init__(self):
            self.fail = True
            self.total = 0

        async def update_balance(self, user_id, guild_id, amount):
            if self.fail:
                raise RuntimeError("temporary database error")
            self.total += amount

    class Bot:
        def __init__(self, bank):
            self.bank = bank

        def get_cog(self, name):
            return self.bank if name == "Economy" else None

    class Response:
        def __init__(self):
            self.messages = []
            self.edits = []

        async def send_message(self, content, **kwargs):
            self.messages.append(content)

        async def edit_message(self, **kwargs):
            self.edits.append(kwargs)

    bank = Bank()
    bot = Bot(bank)
    ctx = SimpleNamespace(
        author=SimpleNamespace(id=7, mention="<@7>", display_name="Tester"),
        guild=SimpleNamespace(id=5),
    )
    game = make_game()
    game.enemy_hp = 1
    view = AnimeClashView(bot, ctx, game)
    response = Response()
    interaction = SimpleNamespace(user=SimpleNamespace(id=7), response=response)
    rolls = iter((16, 200, 16))
    monkeypatch.setattr(clash_mod.random, "randint", lambda *_: next(rolls))

    async def no_sleep(_delay):
        return None

    monkeypatch.setattr(clash_mod.asyncio, "sleep", no_sleep)

    await view.handle_action(interaction, "attack")

    assert game.finished is False
    assert game.settled is False
    assert game.pending_reward == 200
    assert response.messages

    bank.fail = False
    await view.handle_action(interaction, "attack")

    assert bank.total == 200
    assert game.finished is True
    assert game.settled is True
    assert game.pending_reward is None


@pytest.mark.asyncio
async def test_reward_retries_use_one_stable_reference(monkeypatch):
    class Bank:
        def __init__(self):
            self.references = []
            self.total = 0

        async def update_balance(self, user_id, guild_id, amount, *, reference=None):
            self.references.append(reference)
            if len(self.references) <= 3:
                raise RuntimeError("temporary database error")
            self.total += amount

    bank = Bank()
    bot = SimpleNamespace(get_cog=lambda name: bank if name == "Economy" else None)
    ctx = SimpleNamespace(guild=SimpleNamespace(id=5))
    game = make_game()
    view = AnimeClashView(bot, ctx, game)
    delays = []

    async def record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr(clash_mod.asyncio, "sleep", record_sleep)

    assert await view._credit_reward(250) is False
    game.turn += 1
    assert await view._credit_reward(250) is True
    assert bank.total == 250
    assert bank.references == [
        f"animeclash:7:5:{game.game_id}",
        f"animeclash:7:5:{game.game_id}",
        f"animeclash:7:5:{game.game_id}",
        f"animeclash:7:5:{game.game_id}",
    ]
    assert delays == [0.5, 1.0]
