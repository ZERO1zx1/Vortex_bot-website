"""Lottery — тасалбар худалдаж авч, round дуусахад Jackpot сугалах.

Тасалбар бүр **250 ⛃**. Нэг хэрэглэгч нэг round-д дээд тал нь 20 тасалбар
авна. Нийт pot-ийн 96%-ийг нэг ялагч авна (4% house edge).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.exceptions import ValidationError
from core.locks import user_lock
from repositories.log_repo import LogRepository
from repositories.lottery_repo import LotteryRepository, TicketCount
from repositories.user_repo import UserRepository
from services.casino.base import CasinoService
from services.economy.wallet_service import WalletService


@dataclass(frozen=True, slots=True)
class LotteryInfo:
    round_id: int
    tickets: int
    participants: tuple[TicketCount, ...]
    pot: int
    price: int
    max_per_user: int


@dataclass(frozen=True, slots=True)
class LotteryDraw:
    round_id: int
    winner_id: int
    tickets: int
    pot: int
    payout: int
    participants: tuple[TicketCount, ...]


class LotteryService(CasinoService):
    game = "lottery"

    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        wallet: WalletService | None = None,
        lottery: LotteryRepository | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(db, users=users, logs=logs, wallet=wallet, **kwargs)
        self.lottery = lottery or LotteryRepository(db)
        self._round: int | None = None

    async def current_round(self) -> int:
        if self._round is None:
            self._round = await self.lottery.max_round() + 1
        return self._round

    async def info(self, round_id: int | None = None) -> LotteryInfo:
        round_id = await self.current_round() if round_id is None else round_id
        participants = tuple(await self.lottery.participants(round_id))
        tickets = sum(item.tickets for item in participants)
        return LotteryInfo(
            round_id=round_id,
            tickets=tickets,
            participants=participants,
            pot=tickets * config.LOTTERY_TICKET_PRICE,
            price=config.LOTTERY_TICKET_PRICE,
            max_per_user=config.LOTTERY_MAX_TICKETS_PER_ROUND,
        )

    async def buy(
        self,
        user_id: int,
        quantity: int = 1,
        *,
        round_id: int | None = None,
    ) -> LotteryInfo:
        quantity = int(quantity)
        if quantity < 1:
            raise ValidationError("✦ Хамгийн багадаа 1 тасалбар авна.")
        round_id = await self.current_round() if round_id is None else round_id

        async with user_lock("lottery"), user_lock(user_id), self.db.transaction():
            owned = await self.lottery.count_user(user_id, round_id)
            if owned + quantity > config.LOTTERY_MAX_TICKETS_PER_ROUND:
                raise ValidationError(
                    "✦ Нэг round-д дээд тал нь "
                    f"**{config.LOTTERY_MAX_TICKETS_PER_ROUND}** тасалбар авна."
                )
            cost = quantity * config.LOTTERY_TICKET_PRICE
            await self.wallet.spend(
                user_id,
                cost,
                "lottery_ticket",
                metadata={"round": round_id, "quantity": quantity},
            )
            await self.lottery.add_tickets(user_id, round_id, quantity)
        return await self.info(round_id)

    async def draw(self, round_id: int | None = None) -> LotteryDraw:
        round_id = await self.current_round() if round_id is None else round_id
        async with user_lock("lottery"), self.db.transaction():
            tickets = await self.lottery.tickets(round_id)
            if not tickets:
                raise ValidationError("✦ Энэ round-д зарагдсан тасалбар байхгүй.")
            participants = tuple(await self.lottery.participants(round_id))
            winner_id = int(self.rng.choice(tickets))
            pot = len(tickets) * config.LOTTERY_TICKET_PRICE
            payout = self.with_edge(pot)
            await self.wallet.credit(
                winner_id,
                payout,
                "lottery_win",
                metadata={"round": round_id, "tickets": len(tickets)},
            )
            for participant in participants:
                spent = participant.tickets * config.LOTTERY_TICKET_PRICE
                won = payout if participant.user_id == winner_id else 0
                await self.users.add_casino_net(participant.user_id, won - spent)
                await self.logs.record_casino(
                    participant.user_id,
                    "lottery",
                    spent,
                    won,
                    "win" if won else "loss",
                    {
                        "round": round_id,
                        "tickets": participant.tickets,
                        "winner_id": winner_id,
                    },
                )
            await self.lottery.clear_round(round_id)
            self._round = round_id + 1

        await self._award_xp(winner_id, 10)
        return LotteryDraw(
            round_id=round_id,
            winner_id=winner_id,
            tickets=len(tickets),
            pot=pot,
            payout=payout,
            participants=participants,
        )

    async def my_tickets(self, user_id: int) -> int:
        return await self.lottery.count_user(user_id, await self.current_round())
