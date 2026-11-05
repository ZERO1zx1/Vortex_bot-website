"""Regression coverage for the casino money paths.

The contract is the one the repo asserts in tests/test_bugfix_regressions.py:

  * the stake is debited when the hand is dealt;
  * a WIN returns `stake + 10% bonus` (the stake comes back plus the bonus);
  * a LOSS debits the stake exactly once — the settlement used to debit it a
    second time, so a losing player lost twice their bet;
  * a TIE returns the stake.

These tests pin that contract at the pure-function level so a future change
to the settlement cannot silently reintroduce the double charge.
"""
import asyncio

from src.cogs.economy.economy import Economy
from src.cogs.games.casino import blackjack_hand_result

BONUS = 10


def test_blackjack_loss_returns_nothing():
    # Player 17 vs dealer 20 -> lost. The stake is already gone.
    kind, stake_returned, won = blackjack_hand_result(17, 20, 1000)
    assert kind == "loss"
    assert stake_returned == 0
    assert won is False


def test_blackjack_bust_returns_nothing():
    kind, stake_returned, won = blackjack_hand_result(22, 18, 1000)
    assert kind == "bust"
    assert stake_returned == 0
    assert won is False


def test_blackjack_win_returns_the_stake():
    # A win returns the stake; the bonus is added on top of that.
    kind, stake_returned, won = blackjack_hand_result(20, 18, 1000)
    assert kind == "win"
    assert won is True
    assert stake_returned == 1000
    assert stake_returned + int(stake_returned * BONUS / 100) == 1100


def test_blackjack_dealer_bust_is_a_win():
    kind, stake_returned, won = blackjack_hand_result(12, 22, 1000)
    assert kind == "dealer_bust"
    assert won is True
    assert stake_returned == 1000


def test_blackjack_tie_refunds_the_stake():
    kind, stake_returned, won = blackjack_hand_result(18, 18, 1000)
    assert kind == "tie"
    assert stake_returned == 1000
    assert won is False


def test_blackjack_settlement_never_debits_twice():
    """The player's net balance change must never exceed the stake on a loss."""
    stake = 1000
    cases = {
        (17, 20): -stake,      # loss
        (22, 18): -stake,      # bust
        (18, 18): 0,           # tie
        (20, 18): 100,         # win: the bonus is the only net gain
        (12, 22): 100,         # dealer bust
    }
    for (player, dealer), expected in cases.items():
        kind, stake_returned, won = blackjack_hand_result(player, dealer, stake)
        credited = stake_returned + (int(stake_returned * BONUS / 100) if won else 0)
        if kind in ("bust", "loss"):
            # Nothing is returned: the stake was already taken.
            assert credited == 0, f"{kind} returned {credited}"
            net = -stake
        elif kind == "tie":
            assert credited == stake
            net = 0
        else:
            assert credited == stake + int(stake * BONUS / 100)
            net = stake + int(stake * BONUS / 100) - stake
        assert net == expected, f"player={player} dealer={dealer} net={net} != {expected}"


def test_blackjack_double_down_total_stake_is_refunded_on_timeout():
    """A timeout must refund the total stake, not just the opening bet.

    Double-down and split take an extra original_bet, so refunding only
    original_bet silently kept the extra stake.
    """
    from src.cogs.games.casino import BlackjackView

    credited = []

    class FakeEconomy:
        async def update_balance(self, uid, gid, delta, apply_tax=None, **kwargs):
            credited.append(delta)

    class FakeCog:
        def get_cog(self, name):
            return FakeEconomy() if name == "Economy" else None

    class FakeCtx:
        bot = FakeCog()
        author = type("A", (), {"id": 7})()
        guild = type("G", (), {"id": 9})()

    view = object.__new__(BlackjackView)
    view.ctx = FakeCtx()
    view.original_bet = 1000
    view.bet = 2000  # double-down: an extra original_bet was taken
    view.game_over = False
    view.all_hands_resolved = False
    view._children = []  # `children` is a read-only property on discord.ui.View
    view.message = None
    view.stop = lambda: None

    asyncio.run(view.on_timeout())

    assert credited == [2000], f"expected the total stake back, got {credited}"


def test_cooldowns_are_isolated_per_guild():
    """Cooldowns are stored on the economy row, so they are per (user, guild)."""
    economy = object.__new__(Economy)
    rows = {}

    class FakeDB:
        async def update(self, table, filters, data):
            key = (filters.get("user_id"), filters.get("guild_id"))
            rows.setdefault(key, {}).update(data)

    async def get_data(table, filters):
        key = (filters.get("user_id"), filters.get("guild_id"))
        return rows.get(key)

    async def ensure_user(uid, gid):
        rows.setdefault((str(uid), str(gid)), {})

    economy.bot = type("B", (), {"db_manager": FakeDB()})()
    economy.get_data = get_data
    economy.ensure_user = ensure_user

    async def check():
        await economy.set_command_cooldown("42", "100", "last_rob")
        assert await economy.get_command_cooldown("42", "100", "last_rob", 100) > 0
        # A different guild is not affected by the first guild's cooldown.
        assert await economy.get_command_cooldown("42", "200", "last_rob", 100) == 0

    asyncio.run(check())
