from types import SimpleNamespace

import pytest

from src.core.exceptions import DatabaseUnavailableError
from src.cogs.games import leveling
from src.cogs.games.leveling import is_audible_voice_member, xp_for_message


def test_voice_xp_matches_engauge_audibility_rules():
    channel = SimpleNamespace(members=[])
    first = SimpleNamespace(bot=False, voice=SimpleNamespace(channel=channel, mute=False, self_mute=False, deaf=False, self_deaf=False))
    second = SimpleNamespace(bot=False)
    channel.members = [first, second]
    assert is_audible_voice_member(first, channel)

    channel.members = [first]
    assert not is_audible_voice_member(first, channel)

    channel.members = [first, second]
    first.voice.self_mute = True
    assert not is_audible_voice_member(first, channel)


def test_message_xp_accepts_malformed_database_value_without_raising():
    assert xp_for_message("one two", {}) == 15


def test_message_xp_defaults_to_engauge_amount_and_is_configurable():
    assert xp_for_message("one", {}) == 15
    assert xp_for_message("one", {"xp_message": 27}) == 27
    assert xp_for_message("one", {"xp_message": "not-a-number"}) == 15


@pytest.mark.asyncio
async def test_config_outage_keeps_stale_leveling_config():
    guild_id = 987654
    previous = leveling._CFG_CACHE.get(guild_id)
    cfg = {"enabled": False, "xp_message": 27}
    leveling._CFG_CACHE[guild_id] = (0, cfg)

    class UnavailableDB:
        async def fetchone(self, *_args, **_kwargs):
            raise DatabaseUnavailableError("temporary 522")

    try:
        assert await leveling.get_config(UnavailableDB(), guild_id) is cfg
    finally:
        if previous is None:
            leveling._CFG_CACHE.pop(guild_id, None)
        else:
            leveling._CFG_CACHE[guild_id] = previous
