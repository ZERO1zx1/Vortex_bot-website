"""Казиногийн service-үүдийн нийтлэг суурь.

Бүх тоглоом нэг ижил дүрмийг баримтална:
1. Бооцоог `WalletService.lock_funds()`-оор escrow-д түр хаана.
2. Тоглоомын үр дүнг `rng`-ээр тодорхойлно.
3. Хожил/буцаан олголтыг нэг транзакцад бичнэ.
4. `casino_logs`-д зөвхөн INSERT хийнэ, `users.casino_net`-ийг шинэчилнэ.
5. Ялагдсан бооцоонд Lucky Star cashback тооцно.
6. 4% house edge-ийг payout дээр тогтмол хэрэглэнэ.

Энэ файл `discord` импортлохгүй — зөвхөн тооцоолол ба DB.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.locks import user_lock
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService
from services.rpg.skill_service import Modifiers, SkillService
from utils.validators import parse_bet


@dataclass(frozen=True, slots=True)
class CasinoResult:
    game: str
    bet: int
    payout: int
    cashback: int
    net: int
    wallet: int
    outcome: str
    detail: dict[str, Any]
    xp: int = 0


class CasinoService:
    """Бүх казинo service-ийн эцэг класс."""

    game = "casino"

    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        skills: SkillService | None = None,
        wallet: WalletService | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.wallet = wallet or WalletService(db, users=self.users, logs=self.logs)
        self.bus = event_bus
        self.rng = rng or random.Random()

    # ── Туслахууд ──────────────────────────────────────────────────────
    async def modifiers(self, user_id: int) -> Modifiers:
        return await self.skills.get_modifiers(user_id)

    async def _prepare(self, user_id: int, raw_bet: str | int) -> int:
        user = await self.users.get_or_create(user_id)
        return parse_bet(raw_bet, balance=user.wallet)

    async def _lock(self, user_id: int, bet: int) -> None:
        await self.wallet.lock_funds(user_id, bet, source=f"casino_{self.game}_bet")

    async def _finish(
        self,
        user_id: int,
        bet: int,
        payout: int,
        outcome: str,
        detail: dict[str, Any],
        *,
        cashback_eligible: bool = True,
        xp: int = 4,
    ) -> CasinoResult:
        """Хожил, cashback, casino_log, casino_net-ийг нэг дор бичнэ."""
        mods = await self.modifiers(user_id)
        cashback = mods.cashback(bet) if payout == 0 and cashback_eligible else 0
        wallet = (await self.users.get_or_create(user_id)).wallet
        if payout > 0:
            wallet = await self.wallet.credit(
                user_id,
                payout,
                f"casino_{self.game}_payout",
                metadata={"game": self.game, **detail},
            )
        if cashback > 0:
            wallet = await self.wallet.credit(
                user_id,
                cashback,
                "casino_cashback",
                metadata={"game": self.game},
            )
        net = payout - bet + cashback
        await self.users.add_casino_net(user_id, net)
        await self.logs.record_casino(
            user_id,
            self.game,
            bet,
            payout,
            outcome,
            {**detail, "cashback": cashback},
        )
        return CasinoResult(
            game=self.game,
            bet=bet,
            payout=payout,
            cashback=cashback,
            net=net,
            wallet=wallet,
            outcome=outcome,
            detail=detail,
            xp=xp,
        )

    async def _award_xp(self, user_id: int, amount: int) -> None:
        if amount > 0 and self.bus is not None:
            await self.bus.publish(
                XPGained(user_id=user_id, amount=amount, source="casino")
            )

    @staticmethod
    def payout_multiplier(multiplier: float) -> float:
        """4% house edge-тэй нийт буцаах үржүүлэгч."""
        return multiplier * (1.0 - config.CASINO_HOUSE_EDGE)

    @staticmethod
    def with_edge(amount: int) -> int:
        return max(0, int(amount * (1.0 - config.CASINO_HOUSE_EDGE)))

    async def _run(
        self,
        user_id: int,
        raw_bet: str | int,
        play: Any,
    ) -> CasinoResult:
        """Нэг бооцооны бүрэн цикл: escrow → тоглоом → settle → XP.

        `play` нь `(user_id, bet, mods) -> (payout, outcome, detail, xp)`.
        """
        async with user_lock(user_id), self.db.transaction():
            bet = await self._prepare(user_id, raw_bet)
            await self._lock(user_id, bet)
            mods = await self.modifiers(user_id)
            payout, outcome, detail, xp = play(bet, mods)
            result = await self._finish(user_id, bet, payout, outcome, detail, xp=xp)
        await self._award_xp(user_id, result.xp)
        return result
