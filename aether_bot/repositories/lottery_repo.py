"""`lottery_tickets` хүснэгтийн Data Access Layer.

Тасалбар нь append-only биш (сугалаа татсаны дараа тухайн round-ийн
бичлэгүүд устдаг) тул `DELETE` энд зөвшөөрөгдөнө. `transactions` лог нь
үүнийг орлуулахгүй — тасалбарын түүхийг санхүүгийн лог хадгална.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.database import Database


@dataclass(frozen=True, slots=True)
class TicketCount:
    user_id: int
    tickets: int


class LotteryRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def add_ticket(self, user_id: int, round_id: int) -> int:
        return await self.db.insert(
            "INSERT INTO lottery_tickets (user_id, round_id) VALUES (?, ?) "
            "RETURNING ticket_id",
            (user_id, round_id),
        )

    async def add_tickets(self, user_id: int, round_id: int, quantity: int) -> int:
        if quantity <= 0:
            raise ValueError("quantity > 0 байх ёстой")
        await self.db.executemany(
            "INSERT INTO lottery_tickets (user_id, round_id) VALUES (?, ?)",
            [(user_id, round_id) for _ in range(quantity)],
        )
        return quantity

    async def count_user(self, user_id: int, round_id: int) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COUNT(*) FROM lottery_tickets "
                "WHERE user_id = ? AND round_id = ?",
                (user_id, round_id),
                0,
            )
        )

    async def count_round(self, round_id: int) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COUNT(*) FROM lottery_tickets WHERE round_id = ?",
                (round_id,),
                0,
            )
        )

    async def participants(self, round_id: int) -> list[TicketCount]:
        rows = await self.db.fetchall(
            """
            SELECT user_id, COUNT(*) AS tickets
              FROM lottery_tickets
             WHERE round_id = ?
             GROUP BY user_id
             ORDER BY user_id
            """,
            (round_id,),
        )
        return [
            TicketCount(user_id=row["user_id"], tickets=row["tickets"]) for row in rows
        ]

    async def tickets(self, round_id: int) -> list[int]:
        rows = await self.db.fetchall(
            "SELECT user_id FROM lottery_tickets WHERE round_id = ? ORDER BY ticket_id",
            (round_id,),
        )
        return [int(row["user_id"]) for row in rows]

    async def max_round(self) -> int:
        return int(
            await self.db.fetchval(
                "SELECT COALESCE(MAX(round_id), 0) FROM lottery_tickets", (), 0
            )
        )

    async def clear_round(self, round_id: int) -> int:
        return await self.db.execute(
            "DELETE FROM lottery_tickets WHERE round_id = ?", (round_id,)
        )
