"""Wallet: balance, deposit, withdraw, transfer, escrow/payout.

Бүх мөнгө хөдөлгөх метод нь `user_lock` + `db.transaction()` дор ажиллана.
`transactions` хүснэгтэд зөвхөн INSERT хийгдэх бөгөөд `balance_after` нь
тухайн хэрэглэгчийн Wallet-ийн гүйлгээний дараах үлдэгдэл юм.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.database import Database
from core.exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
    ValidationError,
)
from core.locks import multi_user_lock, user_lock
from repositories.guild_repo import GuildRepository
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository, UserRow
from utils.validators import parse_amount


@dataclass(frozen=True, slots=True)
class DepositResult:
    amount: int
    wallet: int
    bank: int


@dataclass(frozen=True, slots=True)
class WithdrawResult:
    amount: int
    wallet: int
    bank: int


@dataclass(frozen=True, slots=True)
class TransferResult:
    amount: int
    tax: int
    net: int
    sender_wallet: int
    recipient_wallet: int


class WalletService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        guilds: GuildRepository | None = None,
        logs: LogRepository | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.guilds = guilds or GuildRepository(db)
        self.logs = logs or LogRepository(db)

    async def balance(self, user_id: int) -> UserRow:
        return await self.users.get_or_create(user_id)

    async def deposit(self, user_id: int, raw_amount: str | int) -> DepositResult:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            amount = parse_amount(raw_amount, balance=user.wallet, allow_all=True)
            if not await self.users.spend_wallet(user_id, amount):
                raise InsufficientFundsError(
                    f"✦ Wallet дээр **{amount:,}** ⛃ байхгүй байна."
                )
            wallet = (await self.users.get(user_id)).wallet  # type: ignore[union-attr]
            bank = await self.users.credit_bank(user_id, amount)
            await self.logs.record_transaction(
                user_id, -amount, "deposit", wallet, {"bank": bank}
            )
        return DepositResult(amount=amount, wallet=wallet, bank=bank)

    async def withdraw(self, user_id: int, raw_amount: str | int) -> WithdrawResult:
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            amount = parse_amount(raw_amount, balance=user.bank, allow_all=True)
            if not await self.users.spend_bank(user_id, amount):
                raise InsufficientFundsError(
                    f"✦ Bank дээр **{amount:,}** ⛃ байхгүй байна."
                )
            bank = (await self.users.get(user_id)).bank  # type: ignore[union-attr]
            wallet = await self.users.credit_wallet(user_id, amount)
            await self.logs.record_transaction(
                user_id, amount, "withdraw", wallet, {"bank": bank}
            )
        return WithdrawResult(amount=amount, wallet=wallet, bank=bank)

    async def transfer(
        self,
        sender_id: int,
        recipient_id: int,
        raw_amount: str | int,
        *,
        guild_id: int | None = None,
    ) -> TransferResult:
        if sender_id == recipient_id:
            raise ValidationError("✦ Өөртөө мөнгө шилжүүлэх боломжгүй.")

        async with multi_user_lock(sender_id, recipient_id), self.db.transaction():
            sender = await self.users.get_or_create(sender_id)
            await self.users.get_or_create(recipient_id)
            amount = parse_amount(raw_amount, balance=sender.wallet, allow_all=True)
            if not await self.users.spend_wallet(sender_id, amount):
                raise InsufficientFundsError(
                    f"✦ Wallet дээр **{amount:,}** ⛃ байхгүй байна."
                )

            tax_pct = await self.guilds.tax_pct(guild_id)
            tax = int(amount * tax_pct)
            net = amount - tax
            sender_wallet = (await self.users.get(sender_id)).wallet  # type: ignore[union-attr]
            recipient_wallet = await self.users.credit_wallet(recipient_id, net)

            await self.logs.record_transaction(
                sender_id,
                -amount,
                "transfer_out",
                sender_wallet,
                {"to": recipient_id, "tax": tax},
            )
            await self.logs.record_transaction(
                recipient_id,
                net,
                "transfer_in",
                recipient_wallet,
                {"from": sender_id, "tax": tax},
            )
        return TransferResult(
            amount=amount,
            tax=tax,
            net=net,
            sender_wallet=sender_wallet,
            recipient_wallet=recipient_wallet,
        )

    # ── Escrow / reward ────────────────────────────────────────────────
    async def lock_funds(
        self, user_id: int, amount: int, *, source: str = "escrow"
    ) -> int:
        """Бооцоог Wallet-оос түр хасаж, үлдсэн балансыг буцаана."""
        if amount <= 0:
            raise InvalidAmountError()
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            if not await self.users.spend_wallet(user_id, amount):
                raise InsufficientFundsError(
                    f"✦ **{amount:,}** ⛃ бооцоонд хүрэлцэхгүй байна."
                )
            user = await self.users.get(user_id)
            assert user is not None
            await self.logs.record_transaction(user_id, -amount, source, user.wallet)
            return user.wallet

    async def credit(
        self,
        user_id: int,
        amount: int,
        source: str,
        *,
        metadata: Any | None = None,
    ) -> int:
        """Орлого/шагнал нэмж, шинэ Wallet-ийг буцаана."""
        if amount < 0:
            raise InvalidAmountError()
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            wallet = await self.users.credit_wallet(user_id, amount)
            await self.logs.record_transaction(
                user_id, amount, source, wallet, metadata
            )
            return wallet

    async def release(
        self,
        user_id: int,
        amount: int,
        *,
        source: str = "escrow_release",
        metadata: Any | None = None,
    ) -> int:
        """Escrow-д түр барьсан мөнгийг эзэнд нь буцаана."""
        return await self.credit(user_id, amount, source, metadata=metadata)

    async def refund(
        self,
        user_id: int,
        amount: int,
        *,
        source: str = "refund",
        metadata: Any | None = None,
    ) -> int:
        """Цуцлагдсан/бүтэлгүй үйлдлийн мөнгийг буцаана."""
        return await self.credit(user_id, amount, source, metadata=metadata)

    async def spend(
        self,
        user_id: int,
        amount: int,
        source: str,
        *,
        metadata: Any | None = None,
    ) -> int:
        """Торгууль/худалдан авалтын зарцуулалт; шинэ Wallet-ийг буцаана."""
        if amount <= 0:
            raise InvalidAmountError()
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            if not await self.users.spend_wallet(user_id, amount):
                raise InsufficientFundsError()
            user = await self.users.get(user_id)
            assert user is not None
            await self.logs.record_transaction(
                user_id, -amount, source, user.wallet, metadata
            )
            return user.wallet
