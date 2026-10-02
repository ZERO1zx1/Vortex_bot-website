from types import SimpleNamespace

import pytest

from src.cogs.admin import Admin
from src.core import config as config_module


class FakeGovernment:
    def __init__(self, co_owner_ids=()):
        self.co_owner_ids = set(co_owner_ids)

    async def is_co_owner_id(self, guild_id, user_id):
        return (int(guild_id), int(user_id)) in self.co_owner_ids


def make_admin(*, global_ids=(), government=None):
    bot = SimpleNamespace(
        owner_ids=set(global_ids),
        get_cog=lambda name: government if name == "Government" else None,
    )
    return Admin(bot)


def make_ctx(user_id, guild_id=5, guild_owner_id=1):
    guild = SimpleNamespace(id=guild_id, owner_id=guild_owner_id)
    return SimpleNamespace(author=SimpleNamespace(id=user_id), guild=guild)


@pytest.mark.asyncio
async def test_admin_owner_check_accepts_global_owner_and_co_owner():
    admin = make_admin(global_ids={10, 11})

    assert await admin.is_owner_or_co_owner(make_ctx(10))
    assert await admin.is_owner_or_co_owner(make_ctx(11))


@pytest.mark.asyncio
async def test_admin_owner_check_accepts_live_guild_owner():
    admin = make_admin()

    assert await admin.is_owner_or_co_owner(make_ctx(1))


@pytest.mark.asyncio
async def test_admin_owner_check_uses_matching_guild_for_government_co_owner():
    government = FakeGovernment({(5, 20)})
    admin = make_admin(government=government)

    assert await admin.is_owner_or_co_owner(make_ctx(20, guild_id=5))
    assert not await admin.is_owner_or_co_owner(make_ctx(20, guild_id=6))
    assert not await admin.is_owner_or_co_owner(make_ctx(99, guild_id=5))


def test_first_run_config_still_applies_owner_and_guild_environment(tmp_path, monkeypatch):
    config_file = tmp_path / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)
    monkeypatch.setenv("OWNER_ID", "100")
    monkeypatch.setenv("CO_OWNERS", "200, 201")
    monkeypatch.setenv("GUILD_ID", "300,301")

    loaded = config_module.load_config()

    assert loaded["owner_id"] == 100
    assert loaded["co_owner_ids"] == [200, 201]
    assert loaded["guild_ids"] == [300, 301]
    assert config_file.exists()
