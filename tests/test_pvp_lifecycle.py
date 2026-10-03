import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.cogs.pvp import PVP, PVPView
from tests.test_bugfix_regressions import FakeBot, FakeEconomySink


def member(uid):
    return SimpleNamespace(id=uid, bot=False, mention=f"<@{uid}>",
                           display_name=str(uid), display_avatar=SimpleNamespace(url="https://example.com/a.png"))


def duel():
    economy = FakeEconomySink()
    bot = FakeBot()
    bot.add_cog("Economy", economy)
    channel = SimpleNamespace(guild=SimpleNamespace(id=5), send=AsyncMock())
    return PVPView(bot, channel, member(1), member(2), 100), economy


@pytest.mark.asyncio
async def test_next_round_does_not_revive_settled_game_during_edit():
    view, economy = duel()
    entered, release = asyncio.Event(), asyncio.Event()

    async def edit(**kwargs):
        if "embed" in kwargs:
            entered.set()
            await release.wait()

    view.message = SimpleNamespace(edit=edit)
    task = asyncio.create_task(view.start_next_round())
    await entered.wait()
    await view.force_end_game()
    release.set()
    await task
    assert not view.game_active and not view.round_active
    assert view._round_timer is None
    assert all(button.disabled for button in view.children)
    assert economy.credits == [100, 100]


@pytest.mark.asyncio
async def test_round_timer_preserves_global_timer_and_idle_timeout_cleans_up():
    view, economy = duel()
    view.round_active = True
    await view.start_global_timer()
    global_timer = view._global_timer
    await view.start_round_timer()
    round_timer = view._round_timer
    assert view._global_timer is global_timer
    assert not global_timer.cancelling()
    await view.timeout_round()
    await asyncio.gather(global_timer, round_timer, return_exceptions=True)
    assert global_timer.cancelled() and round_timer.cancelled()
    await view.force_end_game()
    assert economy.credits == [100, 100]


async def invitation():
    view, economy = duel()
    cog = PVP(view.bot)
    cog.check_cooldown = AsyncMock(return_value=0)
    cog.set_cooldown = AsyncMock()
    message = SimpleNamespace(edit=AsyncMock())
    view.channel.send.return_value = message
    ctx = SimpleNamespace(author=view.player1, guild=view.channel.guild,
                          channel=view.channel, send=view.channel.send)
    await PVP.pvp(cog, ctx, view.player2, "100")
    invite = view.channel.send.call_args.kwargs["view"]
    interaction = SimpleNamespace(user=view.player2, guild_id=5,
                                  response=SimpleNamespace(defer=AsyncMock(),
                                                           edit_message=AsyncMock(),
                                                           send_message=AsyncMock()))
    return invite, interaction, economy


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_send", [1, 2])
async def test_failed_duel_display_refunds_both_entries(failed_send):
    invite, interaction, economy = await invitation()
    invite.channel.send.side_effect = ([RuntimeError("Discord unavailable")] if failed_send == 1
                                      else [SimpleNamespace(), RuntimeError("Discord unavailable")])
    with pytest.raises(RuntimeError, match="Discord unavailable"):
        await invite.accept_button.callback(interaction)
    assert economy.debits == [-100, -100]
    assert economy.credits == [100, 100]
    refunds = economy.payments[-2:]
    assert all(p[3] is False and ":refund:" in p[4] for p in refunds)
    assert invite.is_finished()


@pytest.mark.asyncio
@pytest.mark.parametrize("close_action", ["decline", "timeout"])
async def test_closed_invite_cannot_charge_players(close_action):
    invite, interaction, economy = await invitation()
    if close_action == "decline":
        await invite.decline_button.callback(interaction)
    else:
        await invite.on_timeout()
    await invite.accept_button.callback(interaction)
    assert economy.payments == []
    interaction.response.send_message.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_economy_cannot_start_free_duel():
    invite, interaction, economy = await invitation()
    invite.pvp_cog.bot._cogs.pop("Economy")
    with pytest.raises(RuntimeError, match="Economy is unavailable"):
        await invite.accept_button.callback(interaction)
    assert economy.payments == []
    assert invite.channel.send.await_count == 1  # invitation only
