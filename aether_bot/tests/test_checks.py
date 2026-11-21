from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from discord import app_commands

from core.checks import check_is_admin, check_not_jailed
from core.exceptions import JailedError
from utils.time_utils import to_db, utcnow


class _Repo:
    def __init__(self, user: object | None) -> None:
        self.user = user

    async def get(self, user_id: int) -> object | None:
        return self.user


def _ctx(user: object | None) -> SimpleNamespace:
    return SimpleNamespace(
        author=SimpleNamespace(id=1),
        bot=SimpleNamespace(user_repo=_Repo(user)),
    )


async def test_jailed_user_is_blocked_with_remaining_time() -> None:
    until = to_db(utcnow() + timedelta(minutes=5))
    ctx = _ctx(SimpleNamespace(jail_until=until, jail_bail_cost=250))
    with pytest.raises(JailedError) as exc_info:
        await check_not_jailed(ctx)  # type: ignore[arg-type]
    assert exc_info.value.remaining_sec > 0
    assert exc_info.value.bail_cost == 250
    assert "5" in exc_info.value.user_message or "4" in exc_info.value.user_message


async def test_expired_or_absent_jail_passes() -> None:
    past = to_db(utcnow() - timedelta(minutes=1))
    assert await check_not_jailed(_ctx(None)) is True  # type: ignore[arg-type]
    assert (
        await check_not_jailed(
            _ctx(SimpleNamespace(jail_until=past, jail_bail_cost=0))  # type: ignore[arg-type]
        )
        is True
    )


async def test_missing_user_repo_is_treated_as_free() -> None:
    ctx = SimpleNamespace(author=SimpleNamespace(id=1), bot=SimpleNamespace())
    assert await check_not_jailed(ctx) is True  # type: ignore[arg-type]


class _Client:
    def __init__(self, owner: bool = False) -> None:
        self.owner = owner

    async def is_owner(self, user: object) -> bool:
        return self.owner


def _interaction(*, admin: bool, guild: object | None, owner: bool = False) -> object:
    return SimpleNamespace(
        guild=guild,
        user=SimpleNamespace(guild_permissions=SimpleNamespace(administrator=admin)),
        client=_Client(owner),
    )


async def test_admin_check_allows_administrator_and_owner() -> None:
    guild = object()
    assert await check_is_admin(_interaction(admin=True, guild=guild)) is True
    assert (
        await check_is_admin(_interaction(admin=False, guild=guild, owner=True)) is True
    )


async def test_admin_check_rejects_regular_member_and_dm() -> None:
    with pytest.raises(app_commands.CheckFailure):
        await check_is_admin(_interaction(admin=False, guild=object()))
    with pytest.raises(app_commands.CheckFailure, match="сервер"):
        await check_is_admin(_interaction(admin=False, guild=None))
