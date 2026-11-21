from __future__ import annotations

import pytest

from core.database import Database
from core.exceptions import InsufficientFundsError, ValidationError
from repositories.guild_repo import GuildRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService


async def test_deposit_and_withdraw(db: Database) -> None:
    users = UserRepository(db)
    logs = LogRepository(db)
    wallet = WalletService(db, users=users, logs=logs)

    deposit = await wallet.deposit(1, 300)
    assert (deposit.amount, deposit.wallet, deposit.bank) == (300, 200, 300)
    withdraw = await wallet.withdraw(1, 100)
    assert (withdraw.amount, withdraw.wallet, withdraw.bank) == (100, 300, 200)
    history = await logs.recent_transactions(1)
    assert [row.source for row in history] == ["withdraw", "deposit"]


async def test_transfer_applies_guild_tax(db: Database) -> None:
    users = UserRepository(db)
    guilds = GuildRepository(db)
    logs = LogRepository(db)
    wallet = WalletService(db, users=users, guilds=guilds, logs=logs)
    await users.get_or_create(1)
    await users.get_or_create(2)
    await guilds.set_tax(10, 0.10)

    result = await wallet.transfer(1, 2, 100, guild_id=10)
    assert result.amount == 100
    assert result.tax == 10
    assert result.net == 90
    assert result.sender_wallet == 400
    assert result.recipient_wallet == 590
    assert (await users.get(2)).wallet == 590  # type: ignore[union-attr]


async def test_transfer_rejects_self_and_insufficient(db: Database) -> None:
    wallet = WalletService(db)
    with pytest.raises(ValidationError):
        await wallet.transfer(1, 1, 10)
    with pytest.raises(InsufficientFundsError):
        await wallet.transfer(1, 2, 10_000)


async def test_lock_credit_and_spend(db: Database) -> None:
    users = UserRepository(db)
    wallet = WalletService(db, users=users)
    await users.get_or_create(1)
    assert await wallet.lock_funds(1, 100, source="casino_bet") == 400
    assert await wallet.credit(1, 250, "casino_payout") == 650
    assert await wallet.release(1, 50, source="escrow_release") == 700
    assert await wallet.refund(1, 25, source="refund") == 725
    assert await wallet.spend(1, 50, "shop_buy") == 675
    with pytest.raises(InsufficientFundsError):
        await wallet.lock_funds(1, 10_000)
