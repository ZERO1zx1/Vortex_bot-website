"""3×3 Slots — 5 шугам, тэмдэгт бүрийн үржүүлэгчтэй.

Шугам бүр 3 ижил тэмдэгттэй бол `bet × symbol_multiplier` төлнө.
Нийт хожилд 4% house edge хэрэглэнэ. Олон шугам зэрэг хожно.
"""

from __future__ import annotations

from typing import Any

from services.casino.base import CasinoResult, CasinoService

SYMBOLS: tuple[str, ...] = ("🍒", "🔔", "💎", "⭐", "7️⃣", "✦")
WEIGHTS: tuple[int, ...] = (30, 25, 18, 12, 8, 3)
MULTIPLIERS: dict[str, int] = {
    "🍒": 2,
    "🔔": 3,
    "💎": 5,
    "⭐": 8,
    "7️⃣": 12,
    "✦": 25,
}

LINES: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 4, 8),
    (2, 4, 6),
)


def spin_grid(rng: Any) -> list[str]:
    return list(rng.choices(SYMBOLS, weights=WEIGHTS, k=9))


def winning_lines(grid: list[str], bet: int) -> list[dict[str, Any]]:
    wins: list[dict[str, Any]] = []
    for line in LINES:
        symbols = [grid[index] for index in line]
        if symbols[0] == symbols[1] == symbols[2]:
            wins.append(
                {
                    "line": list(line),
                    "symbol": symbols[0],
                    "multiplier": MULTIPLIERS[symbols[0]],
                    "amount": bet * MULTIPLIERS[symbols[0]],
                }
            )
    return wins


class SlotsService(CasinoService):
    game = "slots"

    async def spin(self, user_id: int, raw_bet: str | int) -> CasinoResult:
        def play(bet: int, mods: Any) -> tuple[int, str, dict[str, Any], int]:
            grid = spin_grid(self.rng)
            wins = winning_lines(grid, bet)
            raw = sum(win["amount"] for win in wins)
            payout = self.with_edge(raw)
            detail = {
                "grid": [grid[0:3], grid[3:6], grid[6:9]],
                "lines": wins,
                "raw_win": raw,
            }
            return payout, "win" if payout > 0 else "loss", detail, 4 if payout else 2

        return await self._run(user_id, raw_bet, play)
