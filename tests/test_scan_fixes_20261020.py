"""Regression coverage for the 2026-10-20 full-scan repairs.

Each test pins one defect that was confirmed by source inspection during the
scan.  They use the same offline style as the rest of the suite: the cog is
rebuilt with ``object.__new__`` and the database is replaced by a fake, so no
Supabase or Discord connection is required.

Covered defects:

* casino   -- the blackjack settlement function was unreachable dead code,
              and the timeout refund was taxed even though the original
              debit was not.
* economy  -- ``update_bank`` silently clamped an overdraft to zero, the tax
              was distributed before the balance write, and ``/crime`` had no
              cooldown at all.
* trade    -- a marketplace listing was claimed by an unconditional delete
              after the money moved, so two buyers could buy one listing.
* shop     -- the item-trade id counter was assigned after a ``return`` and
              never existed, so ``get_trade_id()`` raised AttributeError.
* government -- the treasury was credited with an absolute write derived
              from a cached read, which lost concurrent increments.
* logger   -- log records had no secret redaction filter.
* help     -- the prison commands were registered but undocumented.
"""
import asyncio
import inspect

import pytest

from src.core.exceptions import InsufficientFundsError


# ── helpers ─────────────────────────────────────────────────────────
def _make_economy(balance=100, bank=100):
    """Build an Economy cog with a fake database."""
    from src.cogs.economy.economy import Economy

    economy = object.__new__(Economy)
    economy.max_balance = 1_000_000
    economy._balance_locks = {}
    economy._tax_collected = {}
    economy._tax_distributed = {}
    rows = {
        ("1", "2"): {"user_id": "1", "guild_id": "2", "balance": balance, "bank_balance": bank}
    }

    class FakeDB:
        async def execute(self, table, data):
            rows[(str(data["user_id"]), str(data["guild_id"]))].update(data)

        async def update(self, table, filters, data):
            rows[(str(filters["user_id"]), str(filters["guild_id"]))].update(data)

    economy.db = FakeDB()
    economy.bot = type("B", (), {"db_manager": economy.db})()

    async def get_data(table, filters):
        return rows.get((str(filters["user_id"]), str(filters["guild_id"])))

    async def ensure_user(uid, gid):
        rows.setdefault((str(uid), str(gid)), {"balance": 0, "bank_balance": 0})

    economy.get_data = get_data
    economy.ensure_user = ensure_user
    return economy, rows


# ── casino ──────────────────────────────────────────────────────────
def test_blackjack_settlement_is_reachable():
    """The caller must not pre-set the flag that finalize_game() guards on.

    ``_next_hand_or_finish`` used to set ``self._finalizing = True`` before
    scheduling ``finalize_game``, and ``finalize_game`` starts with
    ``if self._finalizing: return``.  The settlement therefore never ran: no
    win, no loss, no game stats.  Only the timeout refund ever ran.
    """
    from src.cogs.games.casino import BlackjackView

    view = object.__new__(BlackjackView)
    view.hands = [[1, 2]]
    view.active_hand_index = 0
    view._finalizing = False
    scheduled = []

    async def fake_finalize(interaction):
        scheduled.append(interaction)

    view.finalize_game = fake_finalize

    async def run():
        view._next_hand_or_finish("interaction")
        await asyncio.sleep(0)  # let the scheduled task start

    asyncio.run(run())
    assert scheduled == ["interaction"], "finalize_game was never scheduled"

    # The guard that made the settlement unreachable must not come back.
    # finalize_game used to start with `if self._finalizing: return` while
    # the caller had already set that flag, so the function never ran.
    # Comment lines are ignored so the explanation above is not a false hit.
    code = "\n".join(
        line for line in inspect.getsource(BlackjackView.finalize_game).splitlines()
        if not line.strip().startswith("#")
    )
    assert "if self._finalizing:" not in code, (
        "finalize_game must not abort on the caller's own _finalizing flag"
    )


def test_blackjack_settlement_is_scheduled_only_once():
    """Two rapid hand resolutions must not schedule two settlements."""
    from src.cogs.games.casino import BlackjackView

    view = object.__new__(BlackjackView)
    view.hands = [[1, 2]]
    view.active_hand_index = 0
    view._finalizing = False
    scheduled = []

    async def fake_finalize(interaction):
        scheduled.append(interaction)

    view.finalize_game = fake_finalize

    async def run():
        view._next_hand_or_finish("a")
        view._next_hand_or_finish("b")
        await asyncio.sleep(0)

    asyncio.run(run())
    assert scheduled == ["a"], f"settlement scheduled more than once: {scheduled}"


def test_blackjack_timeout_refund_is_untaxed():
    """A cancelled game returns the player's own money, so it is not income.

    The refund is a positive delta, so the default apply_tax=True charged the
    player 10% for a game that never happened.
    """
    from src.cogs.games.casino import BlackjackView

    calls = []

    class FakeEconomy:
        async def update_balance(self, uid, gid, delta, apply_tax=None, **kwargs):
            calls.append((delta, apply_tax))

    class FakeCog:
        def get_cog(self, name):
            return FakeEconomy() if name == "Economy" else None

    view = object.__new__(BlackjackView)
    view.ctx = type("C", (), {
        "bot": FakeCog(),
        "author": type("A", (), {"id": 7})(),
        "guild": type("G", (), {"id": 9})(),
    })()
    view.original_bet = 1000
    view.bet = 2000  # double-down: two stakes were taken
    view.game_over = False
    view.all_hands_resolved = False
    view._children = []
    view.message = None
    view.stop = lambda: None

    asyncio.run(view.on_timeout())

    assert calls == [(2000, False)], f"expected an untaxed full refund, got {calls}"


# ── economy ─────────────────────────────────────────────────────────
def test_update_bank_refuses_an_overdraft():
    """An overdraft must be refused, not silently clamped to zero.

    Clamping let a caller debit more than the bank held and still pay out on
    the full amount, and it destroyed the balance of a concurrent depositor.
    """
    economy, rows = _make_economy(bank=100)

    async def check():
        with pytest.raises(InsufficientFundsError):
            await economy.update_bank("1", "2", -500)
        # A valid withdrawal still works and is written through.
        assert await economy.update_bank("1", "2", -50) == 50
        assert rows[("1", "2")]["bank_balance"] == 50

    asyncio.run(check())


def test_tax_is_distributed_after_the_balance_is_written():
    """The tax must be shipped only after the credit was committed.

    It used to be distributed before the balance write, so a failed write
    paid the collectors from money that was never collected.
    """
    economy, _ = _make_economy(balance=100)
    events = []

    async def update_data(table, data):
        events.append("write_balance")

    async def get_effective_rate(gid):
        return 10

    async def distribute_tax(gid, tax):
        events.append("distribute_tax")
        return tax

    economy.update_data = update_data
    economy.get_effective_rate = get_effective_rate
    economy.distribute_tax = distribute_tax

    async def check():
        return await economy.update_balance("1", "2", 1000)

    balance = asyncio.run(check())
    assert balance == 1000, "1000 credited minus 100 tax"
    assert events == ["write_balance", "distribute_tax"], (
        f"tax must be shipped after the balance write, got {events}"
    )


def test_tax_uses_integer_arithmetic():
    """Integer division, so a 10% tax never rounds up by a floating point error."""
    economy, _ = _make_economy(balance=0)
    seen = {}

    async def update_data(table, data):
        seen.update(data)

    async def get_effective_rate(gid):
        return 10

    async def distribute_tax(gid, tax):
        seen["tax"] = tax
        return tax

    economy.update_data = update_data
    economy.get_effective_rate = get_effective_rate
    economy.distribute_tax = distribute_tax

    async def check():
        await economy.update_balance("1", "2", 333)

    asyncio.run(check())
    assert seen["tax"] == 33, f"expected floor(333 * 10 / 100) = 33, got {seen.get('tax')}"
    assert seen["balance"] == 300


def test_crime_has_a_persistent_cooldown():
    """/crime paid out on every call with no rate limit at all.

    The reward is 1 500-25 000 with a 15-55% success chance, so an
    unthrottled command is an unbounded money faucet.
    """
    from src.cogs.economy.economy import CRIME_COOLDOWN, Economy

    assert CRIME_COOLDOWN > 0, "crime must have a cooldown"

    # The command body must consult the persistent cooldown before paying.
    # `Economy.crime` is a Command object; the coroutine is `.callback`.
    source = inspect.getsource(Economy.crime.callback)
    assert "get_command_cooldown" in source, "crime must check its cooldown"
    assert "set_command_cooldown" in source, "crime must stamp its cooldown"

    economy, _ = _make_economy()
    economy.bot.db_manager = economy.db

    async def check():
        await economy.set_command_cooldown("1", "2", "last_crime")
        assert await economy.get_command_cooldown("1", "2", "last_crime", CRIME_COOLDOWN) > 0
        # A different guild is not affected.
        assert await economy.get_command_cooldown("1", "3", "last_crime", CRIME_COOLDOWN) == 0

    asyncio.run(check())


def test_command_cooldown_rejects_unknown_columns():
    """The cooldown column is interpolated into a query, so it is allow-listed."""
    economy, _ = _make_economy()

    async def check():
        with pytest.raises(ValueError):
            await economy.get_command_cooldown("1", "2", "balance; DROP TABLE economy", 60)
        with pytest.raises(ValueError):
            await economy.set_command_cooldown("1", "2", "nope")

    asyncio.run(check())


# ── trade ───────────────────────────────────────────────────────────
def _make_marketplace(delete_result):
    from src.cogs.shop.trade import Marketplace

    class FakeDB:
        def __init__(self):
            self.deleted = []

        async def delete(self, table, filters):
            self.deleted.append((table, filters))
            return list(delete_result)

    market = object.__new__(Marketplace)
    market.db = FakeDB()
    market.bot = type("B", (), {"db_manager": market.db})()
    return market


def test_claim_listing_returns_the_claimed_row():
    """The listing is claimed by the delete, so only one buyer can win it."""
    row = {
        "id": 5, "guild_id": "1", "seller_id": "2", "item_id": 3,
        "quantity": 1, "price_per_item": 100, "created_at": 1,
    }
    market = _make_marketplace([row])
    claimed = asyncio.run(market.claim_listing(5))
    assert claimed == row
    assert market.db.deleted == [("marketplace_listings", {"id": 5})]


def test_claim_listing_returns_none_when_already_taken():
    """A second buyer gets nothing back, so the purchase must abort."""
    market = _make_marketplace([])
    assert asyncio.run(market.claim_listing(5)) is None


# ── shop ────────────────────────────────────────────────────────────
def test_get_trade_id_never_raises():
    """The counter was assigned after a `return`, so it never existed."""
    from src.cogs.shop.shop import ShopCog

    shop = object.__new__(ShopCog)
    shop._trade_counter = 0
    assert shop.get_trade_id() == 1
    assert shop.get_trade_id() == 2


# ── government ──────────────────────────────────────────────────────
def test_credit_treasury_uses_an_atomic_increment():
    """The treasury must be incremented, not overwritten with a cached total.

    The atomic RPCs increment treasury_balance themselves, so writing an
    absolute value derived from a 15s-stale cache silently lost concurrent
    credits.
    """
    from src.cogs.economy.government import Government

    calls = []

    class FakeDB:
        async def increment(self, table, filters, column, amount):
            calls.append(("increment", table, filters, column, amount))

        async def fetch_one(self, table, filters, selects=None):
            return {"treasury_balance": 100}

        async def upsert(self, table, data, on_conflict=None):
            calls.append(("upsert", table, data))
            return []

    gov = object.__new__(Government)
    gov.db = FakeDB()
    gov.bot = type("B", (), {"db_manager": gov.db})()
    gov._treasury_locks = {}
    gov._settings_cache = {}

    async def get_lock(pool, key):
        lock = pool.get(key)
        if lock is None:
            lock = asyncio.Lock()
            pool[key] = lock
        return lock

    async def add_ledger(**kwargs):
        calls.append(("ledger", kwargs))

    gov._get_lock = get_lock
    gov.add_ledger = add_ledger

    async def check():
        assert await gov.credit_treasury("7", 50, "test") is True

    asyncio.run(check())

    increments = [c for c in calls if c[0] == "increment"]
    assert increments, f"treasury must use an atomic increment, got {calls}"
    assert increments[0][2] == {"guild_id": "7"}
    assert increments[0][3] == "treasury_balance"
    assert increments[0][4] == 50
    assert not [c for c in calls if c[0] == "upsert"], (
        "the treasury must not be written as an absolute value"
    )


# ── logger ──────────────────────────────────────────────────────────
def test_secret_redaction_removes_credentials():
    """Log records had no redaction filter at all."""
    from src.core.logger import redact_secrets

    # Built from parts so the fake credential never appears whole in source
    # (GitHub push protection treats Discord-token-shaped literals as secrets).
    token = ".".join(
        ["MTIzNDU2Nzg5MDEyMzQ1Njc4", "GaBcDe", "FfGgHhIiJjKkLlMmNnOoPpQqRrSsTt"]
    )
    redacted = redact_secrets(f"starting bot with DISCORD_TOKEN={token}")
    assert token not in redacted
    assert "MTIzNDU2Nzg5" not in redacted

    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abcdefghijklmnop"
    assert jwt not in redact_secrets(f"authorization: Bearer {jwt}")

    assert "re_abcdefghijklmnop" not in redact_secrets("api_key=re_abcdefghijklmnop")
    assert "sb_secret_abcdefghijkl" not in redact_secrets("SUPABASE_SECRET_KEY=sb_secret_abcdefghijkl")
    # Ordinary text must survive untouched.
    assert redact_secrets("leveling reward for user 42") == "leveling reward for user 42"


# ── help catalog ────────────────────────────────────────────────────
def test_prison_commands_are_documented():
    """The three prison commands were registered but missing from the catalog."""
    from src.cogs.system.help import COMMAND_INFO

    for name in ("prison", "prison-work", "prison-appeal"):
        assert name in COMMAND_INFO, f"{name} is missing from COMMAND_INFO"
        assert COMMAND_INFO[name]["description_mn"]
        assert COMMAND_INFO[name]["description_en"]
