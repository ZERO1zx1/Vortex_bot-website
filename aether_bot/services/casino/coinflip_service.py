"""Coinflip — Heads/Tails, 1.92x payout (4% house edge)."""

from __future__ import annotations

from typing import Any

from core.exceptions import ValidationError
from services.casino.base import CasinoResult, CasinoService

HEADS = "heads"
TAILS = "tails"
CHOICES = {HEADS, TAILS, "h", "t", "сарьсан", "самрын"}


def normalize_choice(choice: str) -> str:
    value = choice.strip().lower()
    if value in {HEADS, "h", "сарьсан"}:
        return HEADS
    if value in {TAILS, "t", "самрын"}:
        return TAILS
    raise ValidationError("✦ `heads` эсвэл `tails` сонгоно уу.")


class CoinflipService(CasinoService):
    game = "coinflip"

    async def flip(self, user_id: int, raw_bet: str | int, choice: str) -> CasinoResult:
        picked = normalize_choice(choice)

        def play(bet: int, mods: Any) -> tuple[int, str, dict[str, Any], int]:
            landed = self.rng.choice((HEADS, TAILS))
            won = landed == picked
            payout = int(self.payout_multiplier(2.0) * bet) if won else 0
            detail = {"choice": picked, "landed": landed}
            return payout, "win" if won else "loss", detail, 4 if won else 2

        return await self._run(user_id, raw_bet, play)
