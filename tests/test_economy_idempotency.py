import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.cogs.economy import Economy


class AtomicEconomyDB:
    def __init__(self, balance=1_000):
        self.balance = balance
        self.references = {}
        self.lock = asyncio.Lock()
        self.rpc_calls = []

    async def fetch_one(self, table, filters, selects="*"):
        if table != "economy":
            return None
        return {
            "user_id": str(filters["user_id"]),
            "guild_id": str(filters["guild_id"]),
            "balance": self.balance,
        }

    async def fetchone(self, table, filters):
        return await self.fetch_one(table, filters)

    async def execute(self, table, data):
        return None

    async def rpc(self, name, params):
        assert name == "apply_economy_balance_with_tax_once"
        self.rpc_calls.append(dict(params))
        key = params["p_reference"]
        payload = (
            params["p_user_id"],
            params["p_guild_id"],
            params["p_delta"],
            params["p_tax"],
            tuple(sorted((c["user_id"], c["amount"]) for c in params["p_credits"])) if params["p_credits"] else (),
            params["p_treasury"],
            params["p_discarded"],
        )
        async with self.lock:
            existing = self.references.get(key)
            if existing is not None:
                if existing[0] != payload:
                    raise RuntimeError("reference was already used with a different payload")
                return SimpleNamespace(
                    data=[{"applied": False, "balance": existing[1], "tax_shipped": existing[2], "treasury": existing[3]}]
                )

            new_balance = self.balance + params["p_delta"]
            if new_balance < 0:
                raise RuntimeError("insufficient balance")
            self.balance = min(params["p_max_balance"], new_balance)

            # Apply tax credits to our internal state
            tax_shipped = 0
            for credit in params.get("p_credits", []):
                tax_shipped += credit["amount"]
            treasury = params.get("p_treasury", 0)

            self.references[key] = (payload, self.balance, tax_shipped, treasury)
            return SimpleNamespace(data=[{"applied": True, "balance": self.balance, "tax_shipped": tax_shipped, "treasury": treasury}])


class Bot:
    def __init__(self, db):
        self.config = {"tax_percent": 10, "max_balance": 100_000_000}
        self.db_manager = db

    def get_cog(self, _name):
        return None

    def get_guild(self, _guild_id):
        return None


@pytest.mark.asyncio
async def test_same_reference_is_credited_and_taxed_once_across_cog_instances():
    db = AtomicEconomyDB()
    first = Economy(Bot(db))
    second = Economy(Bot(db))

    async def rate(_guild_id):
        return 10

    first.get_effective_rate = rate
    second.get_effective_rate = rate

    balances = await asyncio.gather(
        first.update_balance(7, 5, 100, reference="animeclash:7:5:game-1"),
        second.update_balance(7, 5, 100, reference="animeclash:7:5:game-1"),
    )

    assert balances == [1_090, 1_090]
    assert db.balance == 1_090
    # Tax handled atomically in RPC - verify replay behavior
    assert len(db.rpc_calls) == 2
    # Second call should be a replay (applied=False)
    assert db.rpc_calls[1]["p_delta"] == 90  # credited amount (100 - 10% tax)
    assert db.rpc_calls[1]["p_tax"] == 10
    # With no Government cog, tax is discarded (no credits, no treasury)
    assert db.rpc_calls[1]["p_credits"] == []
    assert db.rpc_calls[1]["p_treasury"] == 0
    assert db.rpc_calls[1]["p_discarded"] == 10


@pytest.mark.asyncio
async def test_reusing_reference_with_different_payload_fails_closed():
    db = AtomicEconomyDB()
    economy = Economy(Bot(db))

    assert await economy.update_balance(
        7, 5, 100, apply_tax=False, reference="reward:one"
    ) == 1_100

    with pytest.raises(RuntimeError, match="different payload"):
        await economy.update_balance(
            7, 5, 101, apply_tax=False, reference="reward:one"
        )
    assert db.balance == 1_100


@pytest.mark.asyncio
async def test_tax_failure_after_commit_does_not_double_credit_or_replay_tax():
    """
    With the new atomic RPC, tax is part of the same transaction as the balance update.
    This test verifies that replaying the same reference returns the committed result
    without re-applying tax credits or balance changes.
    """
    db = AtomicEconomyDB()
    economy = Economy(Bot(db))

    async def rate(_guild_id):
        return 10

    economy.get_effective_rate = rate

    # First call - applies balance + tax atomically
    assert await economy.update_balance(7, 5, 100, reference="reward:tax-failure") == 1_090
    assert db.balance == 1_090
    # With no Government cog, tax is discarded (tax_shipped=0, treasury=0, discarded=10)
    # The reference stores (payload, balance, tax_shipped, treasury)
    ref_data = db.references["reward:tax-failure"]
    assert ref_data[1] == 1_090  # balance
    assert ref_data[2] == 0  # tax_shipped (no Government cog -> no credits)
    assert ref_data[3] == 0  # treasury

    # Second call with same reference - replay, no re-application
    assert await economy.update_balance(7, 5, 100, reference="reward:tax-failure") == 1_090
    assert db.balance == 1_090  # balance unchanged
    assert len(db.rpc_calls) == 2
    # Second call returns applied=False
    assert db.rpc_calls[1]["p_delta"] == 90


@pytest.mark.asyncio
async def test_idempotent_rpc_rejects_insufficient_balance_without_claiming_reference():
    db = AtomicEconomyDB(balance=100)
    economy = Economy(Bot(db))

    with pytest.raises(RuntimeError, match="insufficient balance"):
        await economy.update_balance(
            7, 5, -101, apply_tax=False, reference="debit:too-large"
        )

    assert db.balance == 100
    assert "debit:too-large" not in db.references


@pytest.mark.asyncio
@pytest.mark.parametrize("reference", ["", " ", "x" * 201])
async def test_invalid_reference_is_rejected_before_database_call(reference):
    db = AtomicEconomyDB()
    economy = Economy(Bot(db))

    with pytest.raises(ValueError, match="1-200"):
        await economy.update_balance(7, 5, 100, reference=reference)
    assert db.rpc_calls == []


def test_migration_pins_atomic_claim_and_service_role_boundary():
    migration = Path(
        "src/database/migrations/005_economy_tax_atomic.sql"
    ).read_text(encoding="utf-8")

    assert "reference TEXT PRIMARY KEY" in migration
    assert "ON CONFLICT (reference) DO NOTHING" in migration
    assert "GET DIAGNOSTICS v_claimed_count = ROW_COUNT" in migration
    assert "v_existing.balance_after IS NULL" in migration
    assert "SECURITY DEFINER" in migration
    assert "apply_economy_balance_with_tax_once" in migration
    assert "REVOKE ALL ON FUNCTION apply_economy_balance_with_tax_once" in migration
    assert "GRANT EXECUTE ON FUNCTION apply_economy_balance_with_tax_once" in migration
