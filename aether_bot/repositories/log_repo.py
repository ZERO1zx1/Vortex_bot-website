"""Append-only санхүү/тоглоомын бүртгэлийн Data Access Layer.

`transactions`, `casino_logs`, `game_logs` нь DB trigger-ээр append-only.
Энд зөвхөн INSERT ба SELECT байна — UPDATE/DELETE хэзээ ч бичихгүй.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from core.database import Database, Row
from utils.time_utils import to_db_text


def _json(value: Any | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class TransactionRow:
    tx_id: int
    user_id: int
    amount: int
    source: str
    balance_after: int
    metadata: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> TransactionRow:
        return cls(
            tx_id=row["tx_id"],
            user_id=row["user_id"],
            amount=row["amount"],
            source=row["source"],
            balance_after=row["balance_after"],
            metadata=row["metadata"],
            created_at=to_db_text(row["created_at"]),
        )


@dataclass(frozen=True, slots=True)
class CasinoLogRow:
    log_id: int
    user_id: int
    game: str
    bet: int
    payout: int
    outcome: str
    detail: str | None
    created_at: str

    @classmethod
    def from_row(cls, row: Row) -> CasinoLogRow:
        return cls(
            log_id=row["log_id"],
            user_id=row["user_id"],
            game=row["game"],
            bet=row["bet"],
            payout=row["payout"],
            outcome=row["outcome"],
            detail=row["detail"],
            created_at=to_db_text(row["created_at"]),
        )

    @property
    def net(self) -> int:
        return self.payout - self.bet


@dataclass(frozen=True, slots=True)
class GameLogRow:
    log_id: int
    kind: str
    user_id: int
    opponent_id: int | None
    outcome: str
    reward_coin: int
    reward_xp: int
    detail: str | None
    created_at: str


class LogRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def record_transaction(
        self,
        user_id: int,
        amount: int,
        source: str,
        balance_after: int,
        metadata: Any | None = None,
    ) -> int:
        value = await self.db.fetchval_write(
            """
            INSERT INTO transactions (user_id, amount, source, balance_after, metadata)
            VALUES (?, ?, ?, ?, ?)
            RETURNING tx_id
            """,
            (user_id, amount, source, balance_after, _json(metadata)),
        )
        if value is None:
            raise RuntimeError("transactions мөр хадгалж чадсангүй")
        return int(value)

    async def record_casino(
        self,
        user_id: int,
        game: str,
        bet: int,
        payout: int,
        outcome: str,
        detail: Any | None = None,
    ) -> int:
        value = await self.db.fetchval_write(
            """
            INSERT INTO casino_logs (user_id, game, bet, payout, outcome, detail)
            VALUES (?, ?, ?, ?, ?, ?)
            RETURNING log_id
            """,
            (user_id, game, bet, payout, outcome, _json(detail)),
        )
        if value is None:
            raise RuntimeError("casino_logs мөр хадгалж чадсангүй")
        return int(value)

    async def record_game(
        self,
        kind: str,
        user_id: int,
        outcome: str,
        *,
        opponent_id: int | None = None,
        reward_coin: int = 0,
        reward_xp: int = 0,
        detail: Any | None = None,
    ) -> int:
        value = await self.db.fetchval_write(
            """
            INSERT INTO game_logs
                (kind, user_id, opponent_id, outcome, reward_coin, reward_xp, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING log_id
            """,
            (
                kind,
                user_id,
                opponent_id,
                outcome,
                reward_coin,
                reward_xp,
                _json(detail),
            ),
        )
        if value is None:
            raise RuntimeError("game_logs мөр хадгалж чадсангүй")
        return int(value)

    # ── Унших ──────────────────────────────────────────────────────────
    async def recent_transactions(
        self, user_id: int, limit: int = 10
    ) -> list[TransactionRow]:
        rows = await self.db.fetchall(
            """
            SELECT tx_id, user_id, amount, source, balance_after, metadata, created_at
              FROM transactions
             WHERE user_id = ?
             ORDER BY tx_id DESC
             LIMIT ?
            """,
            (user_id, max(1, int(limit))),
        )
        return [TransactionRow.from_row(row) for row in rows]

    async def recent_casino(self, user_id: int, limit: int = 10) -> list[CasinoLogRow]:
        rows = await self.db.fetchall(
            """
            SELECT log_id, user_id, game, bet, payout, outcome, detail, created_at
              FROM casino_logs
             WHERE user_id = ?
             ORDER BY log_id DESC
             LIMIT ?
            """,
            (user_id, max(1, int(limit))),
        )
        return [CasinoLogRow.from_row(row) for row in rows]

    async def casino_net(self, user_id: int) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COALESCE(SUM(payout - bet), 0) FROM casino_logs "
                "WHERE user_id = ?",
                (user_id,),
                0,
            )
        )

    async def recent_games(self, user_id: int, limit: int = 10) -> list[GameLogRow]:
        rows = await self.db.fetchall(
            """
            SELECT log_id, kind, user_id, opponent_id, outcome, reward_coin,
                   reward_xp, detail, created_at
              FROM game_logs
             WHERE user_id = ?
             ORDER BY log_id DESC
             LIMIT ?
            """,
            (user_id, max(1, int(limit))),
        )
        return [
            GameLogRow(
                log_id=row["log_id"],
                kind=row["kind"],
                user_id=row["user_id"],
                opponent_id=row["opponent_id"],
                outcome=row["outcome"],
                reward_coin=row["reward_coin"],
                reward_xp=row["reward_xp"],
                detail=row["detail"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
