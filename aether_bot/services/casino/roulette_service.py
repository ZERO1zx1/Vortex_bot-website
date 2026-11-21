"""Roulette — 0–36, улаан/хар, тэгш/сонгой, шууд тоо."""

from __future__ import annotations

from typing import Any

from core.exceptions import ValidationError
from services.casino.base import CasinoResult, CasinoService

RED_NUMBERS = frozenset(
    {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
)
BET_TYPES = {"red", "black", "even", "odd", "number"}
ALIASES = {
    "улаан": "red",
    "хар": "black",
    "тэгш": "even",
    "сонгой": "odd",
    "тоо": "number",
}


def color_of(number: int) -> str:
    if number == 0:
        return "green"
    return "red" if number in RED_NUMBERS else "black"


def normalize_bet_type(bet_type: str) -> str:
    value = bet_type.strip().lower()
    value = ALIASES.get(value, value)
    if value not in BET_TYPES:
        raise ValidationError(
            "✦ Бооцооны төрөл: `red`, `black`, `even`, `odd`, `number`."
        )
    return value


class RouletteService(CasinoService):
    game = "roulette"

    async def play(
        self,
        user_id: int,
        raw_bet: str | int,
        bet_type: str,
        number: int | None = None,
    ) -> CasinoResult:
        kind = normalize_bet_type(bet_type)
        if kind == "number":
            if number is None or not 0 <= int(number) <= 36:
                raise ValidationError("✦ Тоо нь **0–36** хооронд байх ёстой.")
            number = int(number)

        def play(bet: int, mods: Any) -> tuple[int, str, dict[str, Any], int]:
            landed = self.rng.randint(0, 36)
            color = color_of(landed)
            won = False
            multiplier = 0.0
            if kind == "red":
                won = color == "red"
                multiplier = 2.0
            elif kind == "black":
                won = color == "black"
                multiplier = 2.0
            elif kind == "even":
                won = landed != 0 and landed % 2 == 0
                multiplier = 2.0
            elif kind == "odd":
                won = landed % 2 == 1
                multiplier = 2.0
            elif kind == "number":
                won = landed == number
                multiplier = 36.0

            payout = self.with_edge(int(bet * multiplier)) if won else 0
            detail = {
                "bet_type": kind,
                "picked": number,
                "landed": landed,
                "color": color,
            }
            return payout, "win" if won else "loss", detail, 4 if won else 2

        return await self._run(user_id, raw_bet, play)
