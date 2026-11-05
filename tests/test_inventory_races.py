"""S10  Inventory and marketplace races.

Both are read-modify-write sequences that were previously unsynchronised:

  S10  ``ShopCog.remove_item`` had no per-item lock, so two concurrent
       consumes of the same stack both read quantity N, both wrote N-1, and
       one item was granted for free (duplication).

  S11  The marketplace checked the buyer's balance *before* a confirmation
       modal that can stay open for a minute, then debited without
       re-checking. A buyer who spent the money during the modal got a raw
       ``InsufficientFundsError`` instead of a clean decline.
"""

import asyncio

import pytest

from src.cogs.shop.shop import ShopCog
from src.core.exceptions import InsufficientFundsError


class RaceDB:
    """In-memory inventory store with a forced await between read and write.

    The forced yield is what makes the race observable: without the lock the
    second coroutine reads the pre-write value before the first one writes.
    """

    def __init__(self, rows=None):
        self.tables = {"user_inventory": list(rows or [])}
        self.writes = 0

    def _row(self, uid, gid, iid):
        for r in self.tables["user_inventory"]:
            if r["user_id"] == str(uid) and r["guild_id"] == str(gid) and r["item_id"] == iid:
                return r
        return None

    async def fetch_one(self, table, filters, selects="*"):
        await asyncio.sleep(0)  # yield: lets a second coroutine interleave
        return self._row(filters["user_id"], filters["guild_id"], filters["item_id"])

    async def update(self, table, filters, values):
        await asyncio.sleep(0)  # yield between read and write
        row = self._row(filters["user_id"], filters["guild_id"], filters["item_id"])
        row.update(values)
        self.writes += 1

    async def delete(self, table, filters):
        row = self._row(filters["user_id"], filters["guild_id"], filters["item_id"])
        if row:
            self.tables["user_inventory"].remove(row)

    async def insert(self, table, data):
        self.tables["user_inventory"].append(dict(data))


def make_shop(rows=None):
    db = RaceDB(rows)
    bot = type("Bot", (), {"db_manager": db})()
    return ShopCog(bot), db


# ══════════════ S10 — inventory duplication ══════════════

@pytest.mark.asyncio
async def test_concurrent_remove_item_cannot_duplicate_stock():
    shop, db = make_shop([{"user_id": "7", "guild_id": "5", "item_id": 1, "quantity": 1}])

    results = await asyncio.gather(
        shop.remove_item(7, 5, 1, 1),
        shop.remove_item(7, 5, 1, 1),
    )

    # Exactly one of two simultaneous consumes of a single item may succeed.
    assert sorted(results) == [False, True]
    # And the row must be gone, not left at quantity 1.
    assert db.tables["user_inventory"] == []


@pytest.mark.asyncio
async def test_concurrent_remove_of_two_from_five_decrements_exactly_once():
    shop, db = make_shop([{"user_id": "7", "guild_id": "5", "item_id": 1, "quantity": 5}])

    results = await asyncio.gather(
        shop.remove_item(7, 5, 1, 2),
        shop.remove_item(7, 5, 1, 2),
    )

    assert all(results)
    # 5 - 2 - 2 == 1. A lost update would leave this at 3.
    assert db.tables["user_inventory"][0]["quantity"] == 1


@pytest.mark.asyncio
async def test_concurrent_add_item_does_not_lose_an_increment():
    shop, db = make_shop([{"user_id": "7", "guild_id": "5", "item_id": 1, "quantity": 10}])

    await asyncio.gather(*(shop.add_item(7, 5, 1, 1) for _ in range(5)))

    assert db.tables["user_inventory"][0]["quantity"] == 15


@pytest.mark.asyncio
async def test_different_items_do_not_block_each_other():
    shop, db = make_shop([
        {"user_id": "7", "guild_id": "5", "item_id": 1, "quantity": 1},
        {"user_id": "7", "guild_id": "5", "item_id": 2, "quantity": 1},
    ])

    results = await asyncio.gather(
        shop.remove_item(7, 5, 1, 1),
        shop.remove_item(7, 5, 2, 1),
    )

    assert all(results)
    assert db.tables["user_inventory"] == []


@pytest.mark.asyncio
async def test_remove_beyond_stock_is_refused_without_writing():
    shop, db = make_shop([{"user_id": "7", "guild_id": "5", "item_id": 1, "quantity": 1}])

    assert await shop.remove_item(7, 5, 1, 5) is False
    assert db.tables["user_inventory"][0]["quantity"] == 1
    assert db.writes == 0


# ══════════════ S11 — marketplace balance race ══════════════

class RaceEconomy:
    """Buyer balance that drops to zero after the pre-modal check."""

    def __init__(self, balance):
        self.balance = balance
        self.debits = []
        self.credits = []

    async def get_balance(self, uid, gid):
        return self.balance

    async def update_balance(self, uid, gid, delta, apply_tax=None, *, reference=None):
        if delta < 0:
            if self.balance + delta < 0:
                raise InsufficientFundsError(f"insufficient balance for user {uid} in guild {gid}")
            self.balance += delta
            self.debits.append(delta)
            return self.balance
        self.balance += delta
        self.credits.append(delta)
        return self.balance


def test_marketplace_rechecks_balance_and_declines_cleanly_on_race():
    """The purchase path must not raise a raw InsufficientFundsError."""
    import inspect

    from src.cogs.shop import trade

    source = inspect.getsource(trade.Marketplace)
    assert "get_balance" in source, "purchase must re-read the balance after confirmation"
    assert "InsufficientFundsError" in source, "purchase must handle the typed error"
    # The re-check must come AFTER the confirmation wait, not before it.
    wait_at = source.index("confirm_view.wait()")
    recheck_at = source.index("get_balance", wait_at)
    assert recheck_at > wait_at
    # And it must be inside the InsufficientFundsError guard.
    assert source.index("try:", recheck_at) < source.index("InsufficientFundsError", recheck_at)


@pytest.mark.asyncio
async def test_insufficient_funds_error_is_a_value_error():
    """Back-compat: typed error must still satisfy legacy `except ValueError`."""
    with pytest.raises(ValueError):
        raise InsufficientFundsError("insufficient balance for user 7 in guild 5")


@pytest.mark.asyncio
async def test_failed_debit_does_not_credit_the_seller():
    eco = RaceEconomy(balance=0)

    with pytest.raises(InsufficientFundsError):
        await eco.update_balance(7, 5, -500)

    assert eco.debits == []
    assert eco.credits == []
