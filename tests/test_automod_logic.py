from types import SimpleNamespace

import pytest

import src.cogs.automod as automod_module
from src.cogs.automod import DEFAULT_ON, AutoModeration


class FakeDB:
    def __init__(self, rows=None):
        self.rows = [dict(row) for row in (rows or [])]

    @staticmethod
    def _matches(row, filters):
        return all(str(row.get(key)) == str(value) for key, value in filters.items())

    async def fetchall(self, table, filters=None):
        return [dict(row) for row in self.rows if not filters or self._matches(row, filters)]

    async def fetchone(self, table, filters):
        return next((dict(row) for row in self.rows if self._matches(row, filters)), None)

    async def update(self, table, filters, data):
        for row in self.rows:
            if self._matches(row, filters):
                row.update(data)
                return [dict(row)]
        return []

    async def insert(self, table, data):
        self.rows.append(dict(data))
        return [dict(data)]


def make_cog(rows=None, guild_ids=(5,)):
    db = FakeDB(rows)
    bot = SimpleNamespace(
        db_manager=db,
        guilds=[SimpleNamespace(id=guild_id) for guild_id in guild_ids],
    )
    return AutoModeration(bot), db


def link_message(content, category_name=None):
    category = SimpleNamespace(name=category_name) if category_name else None
    return SimpleNamespace(content=content, channel=SimpleNamespace(category=category))


def test_link_allowlist_handles_http_https_subdomains_and_blocks_invites():
    cog, _db = make_cog()

    assert cog._is_link_allowed(link_message("http://github.com/openai/codex"))
    assert cog._is_link_allowed(link_message("https://docs.github.com/test"))
    assert not cog._is_link_allowed(link_message("http://evilgithub.com/test"))
    assert not cog._is_link_allowed(link_message("https://discord.gg/example"))
    assert not cog._is_link_allowed(link_message("https://discord.com/invite/example"))


@pytest.mark.asyncio
async def test_load_all_preserves_explicit_all_off_and_defaults_only_without_rows():
    rows = [
        {"guild_id": "5", "feature": feature, "enabled": False}
        for feature in ("antispam", "antilink", "antiraid")
    ]
    rows.append({"guild_id": "7", "feature": "antispam", "enabled": False})
    cog, _db = make_cog(rows, guild_ids=(5, 6, 7))

    await cog._load_all()

    assert cog.enabled[5] == set()
    assert cog.enabled[6] == set(DEFAULT_ON)
    assert cog.enabled[7] == {"antilink"}


@pytest.mark.asyncio
async def test_save_feature_preserves_created_at_on_toggle():
    original = "2026-01-01T00:00:00+00:00"
    cog, db = make_cog([{
        "guild_id": "5",
        "feature": "antispam",
        "enabled": True,
        "created_at": original,
    }])

    await cog._save_feature(5, "antispam", False)

    assert db.rows == [{
        "guild_id": "5",
        "feature": "antispam",
        "enabled": False,
        "created_at": original,
    }]


@pytest.mark.asyncio
async def test_third_spam_violation_kicks(monkeypatch):
    cog, _db = make_cog()
    cog.spam.violations[42] = 2
    calls = {"timeouts": 0, "kicks": 0}

    class Author:
        id = 42
        mention = "<@42>"

        async def timeout(self, until, reason=None):
            calls["timeouts"] += 1

        async def kick(self, reason=None):
            calls["kicks"] += 1

    class Warning:
        async def delete(self):
            return None

    class Channel:
        async def send(self, **kwargs):
            return Warning()

    class Message:
        author = Author()
        channel = Channel()

        async def delete(self):
            return None

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(automod_module.asyncio, "sleep", no_sleep)
    await cog._handle_spam(Message())

    assert calls == {"timeouts": 0, "kicks": 1}
