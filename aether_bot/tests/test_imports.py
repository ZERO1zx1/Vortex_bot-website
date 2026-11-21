from __future__ import annotations

import importlib

import pytest

MODULES = [
    "config",
    "core.database",
    "core.event_bus",
    "core.exceptions",
    "core.locks",
    "core.rate_limiter",
    "core.skill_catalog",
    "utils.time_utils",
    "utils.validators",
    "utils.data_loader",
    "repositories.user_repo",
    "repositories.skill_repo",
    "repositories.shop_repo",
    "repositories.guild_repo",
    "repositories.lottery_repo",
    "services.rpg.skill_service",
    "ui.embeds",
    "ui.common.base",
    "ui.common.modals",
    "ui.common.paginator",
    "ui.system.help_view",
    "cogs.system.help",
    "cogs.system.events",
    "cogs.economy.wallet",
    "cogs.economy.income",
    "cogs.economy.crime",
    "cogs.rpg.profile",
    "cogs.rpg.skills",
    "cogs.rpg.shop",
    "cogs.rpg.inventory",
    "cogs.casino.slots",
    "cogs.casino.blackjack",
    "cogs.casino.roulette",
    "cogs.casino.minefield",
    "cogs.casino.coinflip",
    "cogs.casino.crash",
    "cogs.casino.lottery",
    "cogs.games.duel",
    "cogs.games.adventure",
    "cogs.games.hunt_fish",
    "cogs.games.boss",
    "bot",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_cooldown_error_uses_time_utils() -> None:
    from core.exceptions import CooldownError

    error = CooldownError("Test", 5)
    assert "5с" in error.user_message
