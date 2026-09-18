"""Regression tests for the Critical/High bug-fix pass (C1-C8, H1-H8).

Each test targets one confirmed finding:
  C1  casino high-low loss must debit the bet exactly once
  C2  pvp idle timeout must refund each player exactly once
  C3  blackjack double-down/split wins must pay the actual per-hand stake
  C4  blackjack finalize_game must settle only once
  C5  economy.update_balance must reject overdraw instead of clamping to 0
  C6  transfer re-checks sender balance after confirmation (TOCTOU)
  C7  games give_rewards: no double-charge on loss, tie refunds bet
  C8  games _prep_bet guards balance/cooldown/restrictions before debiting
  H1  /automod uses application-command permission checks
  H2  /rr setup uses application-command permission checks
  H3  automod raid timeout uses a timezone-aware datetime; a failing
      member timeout no longer stops later members
  H4  confession IDs must not repeat after the counter cache is invalidated
  H5  trade buy_selected supports dict listings (no tuple-unpack crash)
  H6  pvp accept is idempotent - double-click starts one duel
  H7  /daily concurrent claims grant the reward once
  H8  counting expression evaluation must reject `**` (DoS vector)

Naming convention mirrors tests/test_mines_logic.py (pytest-asyncio + fakes).
"""
import asyncio
import datetime
import inspect
from types import SimpleNamespace

import discord
import pytest

import src.cogs.casino as casino_mod
import src.cogs.economy as econ_mod
from src.cogs.automod import AutoModeration
from src.cogs.casino import BlackjackView, Casino
from src.cogs.confessions import Confessions
from src.cogs.counting import evaluate_expression
from src.cogs.economy import Economy
from src.cogs.games import Games
from src.cogs.pvp import PVP, PVPView
from src.cogs.reaction_roles import ReactionRoles
from src.cogs.trade import Marketplace


# ══════════════ FAKES ══════════════

class FakeDB:
    """Tiny in-memory stand-in for SupabaseManager (fetch/update/insert)."""

    def __init__(self):
        self.tables = {}

    def _rows(self, table):
        return self.tables.setdefault(table, [])

    @staticmethod
    def _match(row, query):
        return all(str(row.get(k)) == str(v) for k, v in query.items())

    async def fetch_one(self, table, query, selects=None):
        for row in self._rows(table):
            if self._match(row, query):
                if selects:
                    return {selects: row.get(selects)}
                return dict(row)
        return None

    async def fetchone(self, table, query):
        return await self.fetch_one(table, query)

    async def fetch_safe(self, table, query, single=False):
        if not single:
            return await self.fetchall(table, query)
        return await self.fetch_one(table, query)

    async def fetchall(self, table, query=None):
        if query is None:
            return [dict(r) for r in self._rows(table)]
        return [dict(r) for r in self._rows(table) if self._match(r, query)]

    async def fetch_all(self, table, query=None, order_by=None, desc=False,
                        limit=None, offset=None):
        rows = await self.fetchall(table, query)
        if offset:
            rows = rows[offset:]
        if limit:
            rows = rows[:limit]
        return rows

    async def delete(self, table, query):
        rows = self._rows(table)
        kept = [r for r in rows if not self._match(r, query)]
        rows[:] = kept

    async def insert(self, table, data):
        self._rows(table).append(dict(data))

    async def execute(self, table, data):
        query = {"user_id": data.get("user_id"), "guild_id": data.get("guild_id")}
        return await self.update(table, query, data) or self._rows(table).append(dict(data))

    async def update(self, table, query, data):
        for row in self._rows(table):
            if self._match(row, query):
                row.update(dict(data))
                return True
        return False

    async def upsert(self, table, data, on_conflict=None):
        query = {on_conflict: data.get(on_conflict)} if on_conflict else {
            "user_id": data.get("user_id"), "guild_id": data.get("guild_id"),
        }
        for row in self._rows(table):
            if self._match(row, query):
                row.update(dict(data))
                return
        self._rows(table).append(dict(data))


class FakeBot:
    def __init__(self, config=None, db=None):
        self.config = config or {}
        self.db_manager = db or FakeDB()
        self._cogs = {}

    def add_cog(self, name, cog):
        self._cogs[name] = cog

    def get_cog(self, name):
        return self._cogs.get(name)

    def get_guild(self, gid):
        return None


class FakeEconomySink:
    """Fake Economy cog recording +credits and -debits (no tax logic)."""

    def __init__(self, balance=1000):
        self.balance = balance
        self.debits = []
        self.credits = []
        self.bot = SimpleNamespace(db_manager=FakeDB())

    async def update_balance(self, uid, gid, delta):
        if delta < 0:
            self.debits.append(delta)
        else:
            self.credits.append(delta)
        self.balance += delta
        return self.balance

    async def get_balance(self, uid, gid):
        return self.balance

    async def is_in_prison(self, uid, gid):
        return False

    async def ensure_user(self, uid, gid):
        pass

    async def get_hunger_mood(self, uid, gid):
        return (0, 0)


def make_context(bot):
    sent = []

    async def send(embed=None, **kwargs):
        sent.append(embed)

    ctx = SimpleNamespace(
        author=SimpleNamespace(id=7, mention="<@7>", display_name="t", display_avatar=SimpleNamespace(url="u")),
        guild=SimpleNamespace(id=5),
        channel=SimpleNamespace(id=99),
    )
    ctx.send = send
    return ctx, sent


# ══════════════ C5 / C6 — economy update_balance ══════════════

@pytest.mark.asyncio
async def test_update_balance_overdraw_raises_and_keeps_balance():
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": 100}]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    with pytest.raises(ValueError):
        await eco.update_balance(7, 5, -150, apply_tax=False)
    assert await eco.get_balance(7, 5) == 100  # never clamped to 0 (no mint)


@pytest.mark.asyncio
async def test_update_balance_within_balance_debits():
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": 100}]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    assert await eco.update_balance(7, 5, -40, apply_tax=False) == 60


@pytest.mark.asyncio
async def test_update_balance_credit_still_caps_at_max_balance():
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": 100_000_000 - 10}]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    assert await eco.update_balance(7, 5, 100, apply_tax=False) == 100_000_000


@pytest.mark.asyncio
async def test_transfer_race_second_debit_raises_no_mint():
    # Two "transfers" of 80 from a 100₮ balance: the second must refuse,
    # not silently clamp the debit to 0 and create money.
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": 100}]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    assert await eco.update_balance(7, 5, -80, apply_tax=False) == 20
    with pytest.raises(ValueError):
        await eco.update_balance(7, 5, -80, apply_tax=False)
    assert await eco.get_balance(7, 5) == 20


# ══════════════ C7 / C8 — games rewards & guards ══════════════

def make_games(balance=1000):
    eco = FakeEconomySink(balance=balance)
    bot = FakeBot(config={"bonus_percent": 10})
    bot.add_cog("Economy", eco)
    return Games(bot), eco


@pytest.mark.asyncio
async def test_give_rewards_win_credits_winnings_with_bonus():
    games, eco = make_games()
    ctx, _ = make_context(games.bot)

    await games.give_rewards(ctx, 500, 10, won=True, bet=100)

    assert eco.credits == [550]  # 500 + 10% bonus


@pytest.mark.asyncio
async def test_give_rewards_loss_does_not_double_debit():
    # C7: the bet is already deducted in _prep_bet/start_game; a loss must
    # not debit the stake a second time.
    games, eco = make_games()
    ctx, _ = make_context(games.bot)

    await games.give_rewards(ctx, -100, 3, won=False, bet=100)

    assert eco.debits == []
    assert eco.credits == []


@pytest.mark.asyncio
async def test_give_rewards_tie_refunds_bet():
    games, eco = make_games()
    ctx, _ = make_context(games.bot)

    await games.give_rewards(ctx, 0, 4, won=False, bet=100)

    assert eco.credits == [100]


@pytest.mark.asyncio
async def test_prep_bet_insufficient_balance_does_not_debit():
    games, eco = make_games(balance=50)
    ctx, sent = make_context(games.bot)

    assert await games._prep_bet(ctx, "numberguess", 100) is False
    assert eco.debits == []
    assert len(sent) == 1


@pytest.mark.asyncio
async def test_prep_bet_success_debits_once_and_starts_cooldown():
    games, eco = make_games(balance=1000)
    ctx, _ = make_context(games.bot)

    assert await games._prep_bet(ctx, "numberguess", 100) is True
    assert eco.debits == [-100]
    assert await games.is_on_cooldown(7, 5, "numberguess") > 0


# ══════════════ C1 — casino high-low ══════════════

def make_casino(balance=1000):
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": balance}]
    bot = FakeBot(config={"bonus_percent": 10}, db=db)
    eco = Economy(bot)
    bot.add_cog("Economy", eco)
    return Casino(bot), eco


@pytest.mark.asyncio
async def test_highlow_loss_debits_bet_exactly_once(monkeypatch):
    casino, eco = make_casino()
    ctx, _ = make_context(casino.bot)
    values = iter([10, 20])  # first=10, second=20 → "lower" loses
    monkeypatch.setattr(casino_mod.random, "randint", lambda a, b: next(values))

    await casino.highlow_game(ctx, 200, "lower")

    assert await eco.get_balance(7, 5) == 800  # 1000 - 200, nothing extra


@pytest.mark.asyncio
async def test_highlow_win_returns_stake_plus_bonus(monkeypatch):
    casino, eco = make_casino()
    ctx, _ = make_context(casino.bot)
    values = iter([20, 10])  # first=20, second=10 → "lower" wins
    monkeypatch.setattr(casino_mod.random, "randint", lambda a, b: next(values))

    await casino.highlow_game(ctx, 200, "lower")

    # 1000 - 200 (debited up front) + 220 (stake + 10% bonus) - 22 (10% win tax)
    assert await eco.get_balance(7, 5) == 998


# ══════════════ C3 / C4 — blackjack ══════════════

class CasinoStub:
    """Stand-in for the Casino cog used by BlackjackView.finalize_game."""

    def __init__(self):
        self.stats = []

    async def update_game_stats(self, user_id, guild_id, won, bet, win_amt):
        self.stats.append((won, bet, win_amt))

    async def try_give_gem_ring(self, *args, **kwargs):
        pass


def make_blackjack_view(finalizing=False, bet=200, hands=None):
    eco = FakeEconomySink()
    bot = FakeBot(config={"bonus_percent": 10})
    bot.add_cog("Economy", eco)

    view = object.__new__(BlackjackView)
    view._finalizing = finalizing
    view._children = []
    view.bet = bet
    view.hands = hands or [[{"value": 21, "display": "A", "rank": 11}]]
    view.dealer_cards = [{"value": 17, "display": "10", "rank": 10}]
    view.ctx = SimpleNamespace(
        author=SimpleNamespace(id=7, display_name="t", display_avatar=SimpleNamespace(url="u"), mention="<@7>"),
        guild=SimpleNamespace(id=5),
        channel=SimpleNamespace(id=99),
        bot=bot,
    )
    view.casino = CasinoStub()
    return view, eco


@pytest.mark.asyncio
async def test_blackjack_double_down_win_pays_doubled_stake():
    # C3: double down debits 2x bet up front, so a win must pay 2x stake back.
    view, eco = make_blackjack_view(bet=200, hands=[[{"value": 21, "display": "A", "rank": 11}]])

    class Res:
        async def edit_message(self, **kwargs):
            pass
    interaction = SimpleNamespace(response=Res())

    await view.finalize_game(interaction)

    assert eco.credits == [220]  # 200 stake + 10% bonus
    assert view.casino.stats == [(True, 200, 220)]


@pytest.mark.asyncio
async def test_blackjack_finalize_scheduled_once():
    # C4: rapid stand/hit on the last hand must not schedule finalize twice.
    view = object.__new__(BlackjackView)
    view.hands = [["h1"], ["h2"]]
    view.active_hand_index = 0
    view._finalizing = False
    calls = []

    async def after(interaction):
        pass

    async def finalize(interaction):
        calls.append(interaction)

    view._after_hand_switch = after
    view.finalize_game = finalize

    view._next_hand_or_finish("i1")  # switch to hand 2
    view._next_hand_or_finish("i2")  # finalize (first)
    view._next_hand_or_finish("i3")  # ignored (already finalizing)
    await asyncio.sleep(0.05)

    assert calls == ["i2"]


# ══════════════ C2 — pvp double refund ══════════════

@pytest.mark.asyncio
async def test_pvp_idle_timeout_refunds_each_player_once():
    eco = FakeEconomySink()
    bot = FakeBot()
    bot.add_cog("Economy", eco)
    sent = []

    async def send(*args, **kwargs):
        sent.append(args)

    channel = SimpleNamespace(guild=SimpleNamespace(id=5), send=send)
    p1 = SimpleNamespace(id=1, mention="<@1>", display_name="p1")
    p2 = SimpleNamespace(id=2, mention="<@2>", display_name="p2")
    view = PVPView(bot, channel, p1, p2, 100)
    view.round_active = True
    view.player1_ready = False
    view.player2_ready = False

    await view.timeout_round()

    # Exactly one refund per player — a second round trip through end_game
    # (tie branch) used to refund a second time.
    assert eco.credits == [100, 100]
    assert len(sent) == 1


# ══════════════ H4 — confessions counter ══════════════

@pytest.mark.asyncio
async def test_confession_increment_id_never_repeats():
    db = FakeDB()
    db.tables["confession_config"] = [{"guild_id": "5", "next_id": 1}]
    cog = Confessions(FakeBot(db=db))

    assert await cog.increment_id(5) == 1
    assert await cog.increment_id(5) == 2  # regressed to 1 without the cache fix
    assert await cog.increment_id(5) == 3


# ══════════════ H8 — counting pow DoS ══════════════

def test_counting_rejects_pow_expressions():
    assert evaluate_expression("2 + 3 * 4") == 14
    assert evaluate_expression("6 - 4") == 2
    assert evaluate_expression("2 * 3") == 6
    assert evaluate_expression("8 / 4") == 2.0
    assert evaluate_expression("2 ** 3") is None
    assert evaluate_expression("9 ** 9 ** 9") is None


# ══════════════ C3 — blackjack split stake ══════════════

@pytest.mark.asyncio
async def test_blackjack_split_win_uses_per_hand_stake():
    # C3: after a split self.bet == 2 * original, so each of the two hands
    # settles with stake_per_hand = bet // hands (the original bet each).
    view, eco = make_blackjack_view(bet=200, hands=[
        [{"value": 21, "display": "A", "rank": 11}],
        [{"value": 20, "display": "10", "rank": 10}],
    ])

    class Res:
        async def edit_message(self, **kwargs):
            pass
    interaction = SimpleNamespace(response=Res())

    await view.finalize_game(interaction)

    # 100 + 10% bonus per hand, paid as a single settlement
    assert eco.credits == [220]
    assert view.casino.stats == [(True, 100, 110), (True, 100, 110)]


# ══════════════ C6 — transfer TOCTOU: full command flow ══════════════

@pytest.mark.asyncio
async def test_transfer_aborts_when_balance_drops_during_confirm(monkeypatch):
    # Sender has 100, confirms a 80₮ transfer, but during the confirmation
    # window their balance drops to 30. The re-check must abort the transfer:
    # no sender debit, no receiver credit.
    db = FakeDB()
    db.tables["economy"] = [
        {"user_id": "7", "guild_id": "5", "balance": 100},
        {"user_id": "8", "guild_id": "5", "balance": 0},
    ]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    class FakeConfirmView:
        value = True

        async def wait(self):
            row = next(r for r in db.tables["economy"] if r["user_id"] == "7")
            row["balance"] = 30
            return None

    monkeypatch.setattr("src.cogs.economy.ConfirmView", FakeConfirmView)

    member = SimpleNamespace(id=8, mention="<@8>", display_name="r")
    ctx, sent = make_context(eco.bot)

    await Economy.transfer(eco, ctx, member, "80")

    assert await eco.get_balance(7, 5) == 30  # sender NOT debited
    assert await eco.get_balance(8, 5) == 0   # receiver got nothing


# ══════════════ C8 — _prep_bet cooldown & restriction paths ══════════════

@pytest.mark.asyncio
async def test_prep_bet_cooldown_blocks_second_attempt_and_no_debit():
    games, eco = make_games(balance=1000)
    ctx, _ = make_context(games.bot)

    assert await games._prep_bet(ctx, "numberguess", 100) is True
    assert eco.debits == [-100]

    # Still on cooldown → second bet rejected without a second debit.
    assert await games._prep_bet(ctx, "numberguess", 100) is False
    assert eco.debits == [-100]


@pytest.mark.asyncio
async def test_prep_bet_restriction_failure_no_debit():
    class PrisonEconomy(FakeEconomySink):
        async def is_in_prison(self, uid, gid):
            return True

    eco = PrisonEconomy(balance=1000)
    bot = FakeBot(config={"bonus_percent": 10})
    bot.add_cog("Economy", eco)
    games = Games(bot)
    ctx, sent = make_context(bot)

    assert await games._prep_bet(ctx, "numberguess", 100) is False
    assert eco.debits == []
    assert len(sent) == 1  # restriction message sent, nothing debited


# ══════════════ H1 / H2 — slash-command permission metadata ══════════════

def _run_app_command_checks(cmd, permission):
    """Run every local app-command check against a fake interaction with the
    given Permissions for both the user and the bot. A check is considered to
    pass if it returns (truthy) without raising."""
    itx = SimpleNamespace(permissions=permission, app_permissions=permission)
    results = []
    for chk in cmd.checks:
        try:
            res = chk(itx)
            if inspect.isawaitable(res):
                asyncio.get_event_loop().run_until_complete(res)
            results.append(True)
        except Exception:
            results.append(False)
    return results


def test_automod_uses_app_command_permissions():
    cmd = AutoModeration.automod
    assert isinstance(cmd, discord.app_commands.Command)
    assert cmd.default_permissions.manage_guild is True

    # Member + bot both satisfy the requirements -> both checks pass.
    full = discord.Permissions(manage_guild=True, manage_messages=True)
    assert _run_app_command_checks(cmd, full) == [True, True]

    # Bot can manage messages but the member cannot manage guild.
    no_user_perm = discord.Permissions(manage_messages=True)
    assert _run_app_command_checks(cmd, no_user_perm) == [True, False]

    # Member can manage guild but the bot cannot manage messages.
    no_bot_perm = discord.Permissions(manage_guild=True)
    assert _run_app_command_checks(cmd, no_bot_perm) == [False, True]


def test_rr_setup_uses_app_command_permissions():
    cmd = ReactionRoles.rr_setup
    assert isinstance(cmd, discord.app_commands.Command)
    assert cmd.default_permissions.manage_roles is True
    assert _run_app_command_checks(cmd, discord.Permissions(manage_roles=True)) == [True]
    assert _run_app_command_checks(cmd, discord.Permissions()) == [False]


# ══════════════ H3 — automod timeout datetime + failure isolation ══════════════

@pytest.mark.asyncio
async def test_automod_raid_timeout_uses_datetime_and_isolates_failures(monkeypatch):
    db = FakeDB()
    cog = AutoModeration(FakeBot(db=db))
    cog.enabled[5] = {"antiraid"}
    monkeypatch.setattr(cog.raid, "add", lambda guild_id, user_id: [1, 2, 3])

    calls = []

    class FakeTimeoutable:
        def __init__(self, uid, fail=False):
            self.id = uid
            self.fail = fail
            self.created_at = datetime.datetime.now(datetime.timezone.utc)

        def is_timed_out(self):
            return False

        async def timeout(self, until, reason=None):
            calls.append((self.id, until, reason))
            if self.fail:
                raise discord.errors.HTTPException(SimpleNamespace(status=500, reason="Server Error"), "timeout failed")

    class FakeGuild:
        id = 5
        system_channel = None

        def get_member(self, uid):
            if uid == 1:
                return FakeTimeoutable(1)
            if uid == 2:
                return FakeTimeoutable(2, fail=True)
            if uid == 3:
                return FakeTimeoutable(3)
            return None

    guild = FakeGuild()
    member = FakeTimeoutable(2)
    member.guild = guild

    await cog.on_member_join(member)

    # A timeout failure on member 2 must NOT stop members 1 and 3.
    assert [c[0] for c in calls] == [1, 2, 3]
    for uid, until, reason in calls:
        assert isinstance(until, datetime.datetime), "timeout must receive a datetime"
        assert until.tzinfo is not None, "timeout datetime must be timezone-aware"
        assert "Anti-raid" in reason


# ══════════════ H5 — trade dict listing ══════════════

class FakeShop:
    def __init__(self):
        self.added = []
        self.items = {100: {"id": 100, "emoji": "🎁", "name": "Гудамж"} }

    async def get_item(self, item_id):
        return dict(self.items[item_id])

    def get_item_sync(self, item_id):
        return self.items.get(item_id)

    async def add_item(self, user_id, guild_id, item_id, quantity):
        self.added.append((user_id, guild_id, item_id, quantity))


@pytest.mark.asyncio
async def test_trade_buy_selected_handles_dict_listing(monkeypatch):
    # H5: buy_selected previously unpacked the listing as a tuple, crashing
    # with TypeError when Supabase returns a dict row.
    db = FakeDB()
    db.tables["marketplace_listings"] = [
        {"id": 1, "guild_id": "5", "seller_id": "9", "item_id": 100,
         "quantity": 2, "price_per_item": 50},
    ]
    eco = FakeEconomySink(balance=1000)
    shop = FakeShop()
    bot = FakeBot(db=db)
    bot.add_cog("Economy", eco)
    bot.add_cog("ShopCog", shop)
    mkt = Marketplace(bot)

    class FakeConfirmView:
        value = True

        async def wait(self):
            return None

    monkeypatch.setattr("src.cogs.trade.ConfirmView", FakeConfirmView)

    view = Marketplace.ListingsView(mkt, buyer_id=7, page=0)
    view.selected_listing_id = 1

    class FakeResponse:
        async def send_message(self, **kwargs):
            pass

        async def edit_message(self, **kwargs):
            pass

    class FakeFollowup:
        async def send(self, **kwargs):
            pass

    interaction = SimpleNamespace(
        guild_id=5,
        user=SimpleNamespace(id=7, mention="<@7>"),
        guild=SimpleNamespace(get_member=lambda uid: None),
        response=FakeResponse(),
        followup=FakeFollowup(),
    )

    await view.buy_selected(interaction)

    assert shop.added == [(7, 5, 100, 2)]             # item transferred to buyer
    assert db.tables["marketplace_listings"] == []    # listing removed after sale
    assert eco.debits == [-100]                       # buyer debited exactly once
    assert eco.credits == [100]                       # seller credited exactly once


# ══════════════ H6 — PVP accept double-click ══════════════

@pytest.mark.asyncio
async def test_pvp_accept_double_click_starts_one_duel(monkeypatch):
    db = FakeDB()
    eco = FakeEconomySink(balance=5000)
    bot = FakeBot(db=db)
    bot.add_cog("Economy", eco)
    pvp = PVP(bot)

    async def _noop(self, *args, **kwargs):
        pass

    monkeypatch.setattr(PVPView, "send_round_embed", _noop)
    monkeypatch.setattr(PVPView, "start_round_timer", _noop)
    monkeypatch.setattr(PVPView, "start_global_timer", _noop)

    class FakeMember:
        def __init__(self, uid, name):
            self.id = uid
            self.bot = False
            self.mention = f"<@{uid}>"
            self.display_name = name
            self.display_avatar = SimpleNamespace(url="u")

        async def send(self, *args, **kwargs):
            pass

    author = FakeMember(1, "a")
    opponent = FakeMember(2, "b")

    sends = []

    async def fake_send(content=None, embed=None, view=None, **kwargs):
        sends.append((content, embed, view))
        return SimpleNamespace()

    channel = SimpleNamespace(id=9, send=fake_send)
    ctx = SimpleNamespace(author=author, guild=SimpleNamespace(id=5), channel=channel, send=fake_send)

    await PVP.pvp(pvp, ctx, opponent, "100")
    assert sends[0][2] is not None  # the confirmation view was created

    class FakeResponse:
        def __init__(self):
            self.messages = []

        async def send_message(self, content=None, **kwargs):
            self.messages.append((content, kwargs))

    dview = sends[0][2]
    resp = FakeResponse()
    interaction = SimpleNamespace(user=opponent, guild_id=5, response=resp)
    accept_cb = dview.accept_button.callback  # bound (interaction) coroutine

    await accept_cb(interaction)   # first accept -> start_duel
    await accept_cb(interaction)   # second accept -> ignored

    # start_duel debits both players exactly once per accept that proceeds.
    # A double-dispatch here would debit twice and send 2 extra messages.
    assert eco.debits == [-100, -100]
    assert len(sends) == 3  # 1 invite + duel-start + round embed (one start_duel)
    assert any("аль хэдийн" in (m[0] or "") for m in resp.messages)


# ══════════════ H7 — /daily concurrent claim ══════════════

@pytest.mark.asyncio
async def test_daily_concurrent_claims_grant_reward_once(monkeypatch):
    db = FakeDB()
    db.tables["economy"] = [{"user_id": "7", "guild_id": "5", "balance": 0, "last_daily": 0}]
    eco = Economy(FakeBot(config={"tax_percent": 10, "max_balance": 100_000_000}, db=db))

    async def fake_lang(guild_id):
        return "mn"

    monkeypatch.setattr(econ_mod.i18n, "get_guild_lang", fake_lang)
    monkeypatch.setattr(econ_mod.random, "randint", lambda a, b: 10000)

    titles = []

    async def fake_send(*args, **kwargs):
        embed = kwargs.get("embed")
        titles.append(embed.title if embed else None)

    member = SimpleNamespace(id=7, display_avatar=SimpleNamespace(url="u"))
    ctx = SimpleNamespace(author=member, guild=SimpleNamespace(id=5), send=fake_send)

    await asyncio.gather(Economy.daily(eco, ctx), Economy.daily(eco, ctx))

    # Reward granted exactly once: 10000 - 10% tax = 9000.
    assert await eco.get_balance(7, 5) == 9000
    assert titles.count("🎉 Daily Reward") == 1
    assert titles.count("⏰ Daily") == 1