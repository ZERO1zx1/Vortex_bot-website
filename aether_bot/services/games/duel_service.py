"""Duel — 1v1 ээлжит тулаан.

Урсгал:
1. `challenge()` — зөвхөн урилга үүсгэнэ, мөнгө хөдлөхгүй.
2. `accept()` — хоёр тоглогчийн бооцоог `multi_user_lock` дор escrow-д авна.
3. `attack()` — ээлжит довтолгоо/хамгаалалт/Critical Strike.
4. Ялагч нийт pot-ийн 96%-ийг авна (4% house edge), XP хоёуланд нь олгоно.
"""

from __future__ import annotations

import random
import secrets
from dataclasses import dataclass, field

import config
from core.database import Database
from core.event_bus import EventBus, XPGained
from core.exceptions import (
    GameStateError,
    InsufficientFundsError,
    InvalidBetError,
    SkillNotUsableError,
    ValidationError,
)
from core.locks import multi_user_lock
from repositories.log_repo import LogRepository
from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService
from services.rpg.skill_service import SkillService
from utils.validators import parse_quantity

STARTING_HP = 100
WIN_XP = 30
LOSE_XP = 10


@dataclass(slots=True)
class _Duel:
    duel_id: str
    challenger_id: int
    opponent_id: int
    bet: int
    status: str = "pending"  # pending | active | done | declined
    hp: dict[int, int] = field(default_factory=dict)
    defending: set[int] = field(default_factory=set)
    turn_id: int = 0
    log: list[str] = field(default_factory=list)
    winner_id: int | None = None
    payout: int = 0
    xp_winner: int = 0
    xp_loser: int = 0
    wallet: int = 0


@dataclass(frozen=True, slots=True)
class DuelState:
    duel_id: str
    challenger_id: int
    opponent_id: int
    bet: int
    status: str
    challenger_hp: int
    opponent_hp: int
    turn_id: int
    winner_id: int | None = None
    payout: int = 0
    wallet: int = 0
    xp: int = 0
    message: str = ""
    log: tuple[str, ...] = ()


class DuelService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        logs: LogRepository | None = None,
        wallet: WalletService | None = None,
        skills: SkillService | None = None,
        event_bus: EventBus | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.logs = logs or LogRepository(db)
        self.wallet = wallet or WalletService(db, users=self.users, logs=self.logs)
        self.skills = skills or SkillService(db, user_repo=self.users)
        self.bus = event_bus
        self.rng = rng or random.Random()
        self._duels: dict[str, _Duel] = {}

    def _require(self, duel_id: str) -> _Duel:
        duel = self._duels.get(duel_id)
        if duel is None:
            raise GameStateError()
        return duel

    def _state(self, duel: _Duel, *, message: str = "") -> DuelState:
        return DuelState(
            duel_id=duel.duel_id,
            challenger_id=duel.challenger_id,
            opponent_id=duel.opponent_id,
            bet=duel.bet,
            status=duel.status,
            challenger_hp=duel.hp.get(duel.challenger_id, STARTING_HP),
            opponent_hp=duel.hp.get(duel.opponent_id, STARTING_HP),
            turn_id=duel.turn_id,
            winner_id=duel.winner_id,
            payout=duel.payout,
            wallet=duel.wallet,
            xp=duel.xp_winner,
            message=message,
            log=tuple(duel.log[-3:]),
        )

    async def challenge(
        self, challenger_id: int, opponent_id: int, raw_bet: str | int
    ) -> DuelState:
        if challenger_id == opponent_id:
            raise ValidationError("✦ Өөртэйгөө тулалдах боломжгүй.")
        bet = parse_quantity(
            raw_bet,
            minimum=config.DUEL_MIN_BET,
            maximum=config.DUEL_MAX_BET,
            error=InvalidBetError,
        )
        challenger = await self.users.get_or_create(challenger_id)
        opponent = await self.users.get_or_create(opponent_id)
        if challenger.wallet < bet:
            raise InsufficientFundsError(
                f"✦ Challenger-ийн Wallet дээр **{bet:,}** ⛃ байхгүй."
            )
        if opponent.wallet < bet:
            raise InsufficientFundsError(
                f"✦ Opponent-ийн Wallet дээр **{bet:,}** ⛃ байхгүй."
            )
        duel = _Duel(
            duel_id=secrets.token_hex(4),
            challenger_id=challenger_id,
            opponent_id=opponent_id,
            bet=bet,
            hp={challenger_id: STARTING_HP, opponent_id: STARTING_HP},
            turn_id=challenger_id,
            log=["⚔️ Урилга илгээгдлээ."],
        )
        self._duels[duel.duel_id] = duel
        return self._state(duel, message="✦ Duel урилга бэлэн.")

    async def accept(self, duel_id: str, user_id: int) -> DuelState:
        duel = self._require(duel_id)
        if duel.status != "pending":
            raise GameStateError("✦ Энэ duel аль хэдийн эхэлсэн эсвэл цуцлагдсан.")
        if user_id != duel.opponent_id:
            raise ValidationError("✦ Зөвхөн уригдсан тоглогч хүлээн авна.")

        async with (
            multi_user_lock(duel.challenger_id, duel.opponent_id),
            self.db.transaction(),
        ):
            await self.wallet.lock_funds(
                duel.challenger_id, duel.bet, source="duel_bet"
            )
            await self.wallet.lock_funds(duel.opponent_id, duel.bet, source="duel_bet")
            duel.status = "active"
            duel.log.append("🔥 Duel эхэллээ.")
        return self._state(duel)

    async def decline(self, duel_id: str, user_id: int) -> DuelState:
        duel = self._require(duel_id)
        if user_id != duel.opponent_id:
            raise ValidationError("✦ Зөвхөн уригдсан тоглогч татгалзана.")
        if duel.status != "pending":
            raise GameStateError()
        duel.status = "declined"
        duel.log.append("✖️ Урилга татгалзагдлаа.")
        self._duels.pop(duel_id, None)
        return self._state(duel)

    async def attack(
        self, duel_id: str, user_id: int, move: str = "attack"
    ) -> DuelState:
        duel = self._require(duel_id)
        if duel.status != "active":
            raise GameStateError("✦ Duel идэвхтэй биш байна.")
        if user_id != duel.turn_id:
            raise GameStateError("✦ Одоо таны ээлж биш.")
        move = move.strip().lower()
        if move not in {"attack", "defend", "skill"}:
            raise ValidationError(
                "✦ `attack`, `defend`, `skill`-ийн нэгийг сонгоно уу."
            )
        target_id = (
            duel.opponent_id if user_id == duel.challenger_id else duel.challenger_id
        )

        finished: DuelState | None = None
        async with (
            multi_user_lock(duel.challenger_id, duel.opponent_id),
            self.db.transaction(),
        ):
            message: str
            if move == "defend":
                duel.defending.add(user_id)
                message = "🛡️ Хамгаалалтад орлоо."
            else:
                critical = False
                if move == "skill":
                    if not await self.skills.consume_charge(user_id, "critical_strike"):
                        raise SkillNotUsableError(
                            "✦ Critical Strike цэнэг идэвхгүй байна."
                        )
                    critical = True
                damage = self.rng.randint(10, 22)
                if critical:
                    damage = int(damage * 1.5)
                if target_id in duel.defending:
                    damage = max(1, damage // 2)
                    duel.defending.discard(target_id)
                duel.hp[target_id] = max(0, duel.hp[target_id] - damage)
                message = (
                    f"💥 **{damage}** damage"
                    + (" (Critical!)" if critical else "")
                    + f" → <@{target_id}>"
                )

            duel.log.append(message)
            if duel.hp[target_id] <= 0:
                finished = await self._finish_locked(duel, user_id)
            else:
                duel.turn_id = target_id

        if finished is not None:
            await self._award_xp(duel)
            return finished
        return self._state(duel, message=message)

    async def _finish_locked(self, duel: _Duel, winner_id: int) -> DuelState:
        loser_id = (
            duel.opponent_id if winner_id == duel.challenger_id else duel.challenger_id
        )
        payout = int(duel.bet * 2 * (1.0 - config.CASINO_HOUSE_EDGE))
        duel.wallet = await self.wallet.credit(
            winner_id,
            payout,
            "duel_win",
            metadata={"opponent": loser_id, "bet": duel.bet},
        )
        duel.winner_id = winner_id
        duel.payout = payout
        duel.status = "done"
        duel.xp_winner = WIN_XP
        duel.xp_loser = LOSE_XP
        duel.log.append(f"🏆 <@{winner_id}> ялав.")
        await self.logs.record_game(
            "duel",
            winner_id,
            "win",
            opponent_id=loser_id,
            reward_coin=payout,
            reward_xp=WIN_XP,
            detail={"bet": duel.bet},
        )
        await self.logs.record_game(
            "duel",
            loser_id,
            "loss",
            opponent_id=winner_id,
            reward_coin=0,
            reward_xp=LOSE_XP,
            detail={"bet": duel.bet},
        )
        self._duels.pop(duel.duel_id, None)
        return self._state(duel, message="✦ Duel дууслаа.")

    async def _award_xp(self, duel: _Duel) -> None:
        if self.bus is None or duel.winner_id is None:
            return
        loser_id = (
            duel.opponent_id
            if duel.winner_id == duel.challenger_id
            else duel.challenger_id
        )
        await self.bus.publish(
            XPGained(user_id=duel.winner_id, amount=WIN_XP, source="duel")
        )
        await self.bus.publish(
            XPGained(user_id=loser_id, amount=LOSE_XP, source="duel")
        )
