"""S13  XP drop admin panel + `xp_drop_interval` actually honoured.

The engine loop, the `XPDropView` claim guard and every `xp_drop_*` database
column already existed, but nothing in the whole cog tree ever WROTE
`xp_drop_enabled` — the feature could only be switched on by hand-editing the
`leveling_config` row in Supabase. `xp_drop_interval` was read into the config
dict and then never used at all.

These tests lock both halves down.
"""

import inspect
import re
from types import SimpleNamespace
from typing import ClassVar

import pytest

from src.cogs.admin import level_admin as level_admin_mod
from src.cogs.admin.level_admin import LevelingSetupView, XPDropSettingsView
from src.cogs.games import leveling as leveling_mod
from src.cogs.games.leveling import Leveling


@pytest.fixture(autouse=True)
def _clear_config_cache():
    """`get_config` keeps a TTL cache; without this every test would reuse the
    config written by the previous one."""
    leveling_mod._CFG_CACHE.clear()
    yield
    leveling_mod._CFG_CACHE.clear()


# ── S13a — the panel exists and writes every xp_drop_* key ──────────

def test_xp_drop_panel_is_reachable_from_the_setup_panel():
    src = inspect.getsource(LevelingSetupView)
    assert "XPDropSettingsView" in src, "setup panel must offer the XP drop panel"


def test_panel_writes_the_enabled_flag():
    src = inspect.getsource(XPDropSettingsView)
    assert "xp_drop_enabled" in src
    assert "set_config" in src


def test_panel_writes_channel_amounts_and_interval():
    src = inspect.getsource(level_admin_mod)
    for key in ("xp_drop_channel", "xp_drop_min", "xp_drop_max", "xp_drop_interval"):
        assert key in src, f"{key} must be configurable from the panel"


def test_panel_only_touches_xp_drop_keys():
    """Opening the panel must never flip the whole leveling system."""
    src = inspect.getsource(XPDropSettingsView)
    assert 'cfg["enabled"]' not in src
    assert "toggle=True" not in src


# ── S13b — the loop honours xp_drop_interval ───────────────────────

def _loop_source() -> str:
    # `xp_drop_loop` is a discord.ext.tasks.Loop, which exposes no readable
    # callback, so slice the coroutine body out of the module source.
    src = inspect.getsource(leveling_mod)
    start = src.index("async def xp_drop_loop")
    end = src.index("\n    @", start + 10)
    return src[start:end]


def test_loop_actually_uses_the_interval():
    src = _loop_source()
    assert 'cfg["xp_drop_interval"]' in src, "loop must read xp_drop_interval"
    assert "_xp_drop_last" in src, "loop must track the last drop per guild"


def test_loop_timestamp_state_is_initialised():
    src = inspect.getsource(Leveling.__init__)
    assert "_xp_drop_last" in src


# ── S13c — behavioural test of the interval gate ───────────────────

class _CfgDB:
    def __init__(self, cfg):
        self._cfg = cfg

    async def fetchone(self, table, filters):
        return dict(self._cfg) if table == "leveling_config" else None

    async def fetch_all(self, *a, **k):
        return []


def _engine(cfg):
    db = _CfgDB(cfg)
    bot = SimpleNamespace(db_manager=db, get_cog=lambda n: None)
    lv = Leveling(bot)
    return lv


class _Guild:
    def __init__(self, channel):
        self.id = 5
        self._channel = channel

    def get_channel(self, cid):
        return self._channel if self._channel and self._channel.id == cid else None


class _Channel:
    id = 99
    sent: ClassVar[list] = []

    async def send(self, **kw):
        _Channel.sent.append(kw)
        return SimpleNamespace()


def _cfg(**over):
    base = {
        "enabled": True,
        "xp_drop_enabled": True,
        "xp_drop_channel": 99,
        "xp_drop_min": 100,
        "xp_drop_max": 500,
        "xp_drop_interval": 3600,
    }
    base.update(over)
    return base


@pytest.mark.asyncio
async def test_second_drop_is_suppressed_inside_the_interval(monkeypatch):
    lv = _engine(_cfg())
    lv.bot.guilds = [_Guild(_Channel())]
    _Channel.sent.clear()

    monkeypatch.setattr("src.cogs.games.leveling.random.random", lambda: 0.0)  # always roll a drop

    await lv.xp_drop_loop()
    assert len(_Channel.sent) == 1, "first drop must be allowed"

    # Immediately after: the interval has not elapsed -> suppressed.
    await lv.xp_drop_loop()
    assert len(_Channel.sent) == 1, "second drop inside the interval must be blocked"

    # Past the interval -> allowed again.
    lv._xp_drop_last[5] -= 3601
    await lv.xp_drop_loop()
    assert len(_Channel.sent) == 2, "drop must resume once the interval elapses"


@pytest.mark.asyncio
async def test_zero_interval_is_floored_so_the_loop_cannot_spin(monkeypatch):
    lv = _engine(_cfg(xp_drop_interval=0))
    lv.bot.guilds = [_Guild(_Channel())]
    _Channel.sent.clear()
    monkeypatch.setattr("src.cogs.games.leveling.random.random", lambda: 0.0)

    await lv.xp_drop_loop()
    await lv.xp_drop_loop()
    # interval floored to 60s -> still suppressed on the second tick.
    assert len(_Channel.sent) == 1


@pytest.mark.asyncio
async def test_disabled_feature_never_posts(monkeypatch):
    lv = _engine(_cfg(xp_drop_enabled=False))
    lv.bot.guilds = [_Guild(_Channel())]
    _Channel.sent.clear()
    monkeypatch.setattr("src.cogs.games.leveling.random.random", lambda: 0.0)

    await lv.xp_drop_loop()
    assert _Channel.sent == []


@pytest.mark.asyncio
async def test_missing_channel_never_posts(monkeypatch):
    lv = _engine(_cfg())
    lv.bot.guilds = [_Guild(None)]
    _Channel.sent.clear()
    monkeypatch.setattr("src.cogs.games.leveling.random.random", lambda: 0.0)

    await lv.xp_drop_loop()
    assert _Channel.sent == []


# ── S13d — one claim per user (regression guard) ───────────────────

def test_xp_drop_claim_is_guarded_against_double_claim():
    # XPDropView is a module-level class, not a member of Leveling.
    src = inspect.getsource(leveling_mod)
    view_src = re.search(r"class XPDropView.*?(?=\nclass |\Z)", src, re.DOTALL)
    assert view_src, "XPDropView must still exist"
    body = view_src.group(0)
    assert "self.claimed" in body
    assert "interaction.user.id in self.claimed" in body


@pytest.mark.asyncio
async def test_concurrent_claims_by_one_user_grant_once():
    """The claim guard must be checked before the XP is granted."""
    from src.cogs.games.leveling import XPDropView

    view = XPDropView(250, SimpleNamespace(add_xp=_record()))
    granted = []

    async def add_xp(user_id, guild_id, amount, member=None, **kw):
        granted.append(amount)

    view.cog = SimpleNamespace(add_xp=add_xp)
    user = SimpleNamespace(id=42)

    interaction = SimpleNamespace(
        user=user,
        guild=SimpleNamespace(id=5, get_member=lambda uid: None),
        response=SimpleNamespace(send_message=_capture()),
    )
    # `view.claim` is a Button; discord.py binds the item, so `.callback`
    # takes only the interaction.
    await view.claim.callback(interaction)
    await view.claim.callback(interaction)
    assert granted == [250], "a second click must not grant XP again"


def _record():
    async def noop(*a, **k):
        return None
    return noop


def _capture():
    async def send_message(*a, **k):
        return None
    return send_message
