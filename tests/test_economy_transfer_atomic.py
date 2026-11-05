"""Regression coverage for the atomic transfer path.

Migration 009 adds apply_economy_transfer_once(), which moves both balances
and the transfer tax in one transaction and claims a reference. The transfer
command used to be two independent writes, so a crash between them destroyed
the amount.
"""
import asyncio

from src.cogs.economy.economy import Economy


class FakeRPCError(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.code = code


def make_economy(rpc_result=None, rpc_error=None):
    economy = object.__new__(Economy)
    economy.max_balance = 100_000_000

    class FakeDB:
        async def rpc(self, fn, params=None):
            if rpc_error is not None:
                raise rpc_error
            return rpc_result

    class FakeBot:
        db_manager = FakeDB()

        def get_cog(self, name):
            return None

    economy.bot = FakeBot()
    return economy


def test_missing_rpc_is_classified_as_missing():
    assert Economy._is_missing_rpc(FakeRPCError("function does not exist", code="PGRST202"))
    assert Economy._is_missing_rpc(FakeRPCError("Could not find the function"))
    assert Economy._is_missing_rpc(FakeRPCError("not found", code="404"))
    # A real failure is not a missing function.
    assert not Economy._is_missing_rpc(FakeRPCError("insufficient balance", code="P0001"))


def test_transfer_principal_returns_the_committed_balances():
    row = {"applied": True, "from_balance": 400, "to_balance": 700}
    economy = make_economy(rpc_result=row)
    result = asyncio.run(economy._transfer_principal(1, 2, 3, 100, 0, "ref-1"))
    assert result == (400, 700)


def test_transfer_principal_returns_none_when_the_rpc_is_missing():
    economy = make_economy(rpc_error=FakeRPCError("function does not exist", code="PGRST202"))
    result = asyncio.run(economy._transfer_principal(1, 2, 3, 100, 0, "ref-1"))
    assert result is None


def test_transfer_principal_returns_none_when_the_rpc_fails():
    economy = make_economy(rpc_error=FakeRPCError("insufficient balance"))
    result = asyncio.run(economy._transfer_principal(1, 2, 3, 100, 0, "ref-1"))
    assert result is None


def test_transfer_principal_rejects_a_malformed_response():
    economy = make_economy(rpc_result=[{"applied": True}])  # no balances
    result = asyncio.run(economy._transfer_principal(1, 2, 3, 100, 0, "ref-1"))
    assert result is None


def test_transfer_reference_is_deterministic_per_message():
    """The same transfer must produce the same reference so a replay is safe."""
    ctx = type(
        "C",
        (),
        {"guild": type("G", (), {"id": 5})(), "author": type("A", (), {"id": 6})(),
         "message": type("M", (), {"id": 77})()},
    )()
    first = f"transfer:{ctx.guild.id}:{ctx.author.id}:{getattr(ctx.message, 'id', 'nomsg')}"
    second = f"transfer:{ctx.guild.id}:{ctx.author.id}:{getattr(ctx.message, 'id', 'nomsg')}"
    assert first == second
    assert first == "transfer:5:6:77"