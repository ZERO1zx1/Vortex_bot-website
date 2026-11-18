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
    "repositories.user_repo",
    "repositories.skill_repo",
    "services.rpg.skill_service",
    "ui.embeds",
    "cogs.health",
    "cogs.economy",
    "cogs.skills",
    "cogs.admin",
    "bot",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module: str) -> None:
    assert importlib.import_module(module) is not None


def test_cooldown_error_uses_time_utils() -> None:
    from core.exceptions import CooldownError

    error = CooldownError("Test", 5)
    assert "5с" in error.user_message
