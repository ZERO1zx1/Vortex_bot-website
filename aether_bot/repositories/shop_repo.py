"""`shop_items`, `inventory`, `user_effects` хүснэгтүүдийн Data Access Layer."""

from __future__ import annotations

from dataclasses import dataclass

import aiosqlite

from core.database import Database


@dataclass(frozen=True, slots=True)
class ShopItemRow:
    item_id: str
    name: str
    category: str
    price: int
    description: str
    effect_type: str
    effect_value: float
    duration_sec: int
    icon: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> ShopItemRow:
        return cls(
            item_id=row["item_id"],
            name=row["name"],
            category=row["category"],
            price=row["price"],
            description=row["description"],
            effect_type=row["effect_type"],
            effect_value=row["effect_value"],
            duration_sec=row["duration_sec"],
            icon=row["icon"],
        )


@dataclass(frozen=True, slots=True)
class InventoryRow:
    item: ShopItemRow
    quantity: int


@dataclass(frozen=True, slots=True)
class EffectRow:
    effect_id: int
    user_id: int
    effect_type: str
    value: float
    expires_at: str
    created_at: str

    @classmethod
    def from_row(cls, row: aiosqlite.Row) -> EffectRow:
        return cls(
            effect_id=row["effect_id"],
            user_id=row["user_id"],
            effect_type=row["effect_type"],
            value=row["value"],
            expires_at=row["expires_at"],
            created_at=row["created_at"],
        )


_ITEM_SELECT = """
    SELECT item_id, name, category, price, description, effect_type,
           effect_value, duration_sec, icon
      FROM shop_items
"""


class ShopRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    # ── Catalog ────────────────────────────────────────────────────────
    async def list_items(self, category: str | None = None) -> list[ShopItemRow]:
        if category:
            rows = await self.db.fetchall(
                f"{_ITEM_SELECT} WHERE category = ? ORDER BY price, item_id",
                (category,),
            )
        else:
            rows = await self.db.fetchall(
                f"{_ITEM_SELECT} ORDER BY category, price, item_id"
            )
        return [ShopItemRow.from_row(row) for row in rows]

    async def get_item(self, item_id: str) -> ShopItemRow | None:
        row = await self.db.fetchone(f"{_ITEM_SELECT} WHERE item_id = ?", (item_id,))
        return ShopItemRow.from_row(row) if row else None

    async def upsert_item(self, item: ShopItemRow) -> None:
        await self.db.execute(
            """
            INSERT INTO shop_items
                (item_id, name, category, price, description, effect_type,
                 effect_value, duration_sec, icon)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(item_id) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                price = excluded.price,
                description = excluded.description,
                effect_type = excluded.effect_type,
                effect_value = excluded.effect_value,
                duration_sec = excluded.duration_sec,
                icon = excluded.icon
            """,
            (
                item.item_id,
                item.name,
                item.category,
                item.price,
                item.description,
                item.effect_type,
                item.effect_value,
                item.duration_sec,
                item.icon,
            ),
        )

    async def delete_item(self, item_id: str) -> bool:
        return (
            await self.db.execute(
                "DELETE FROM shop_items WHERE item_id = ?", (item_id,)
            )
            == 1
        )

    # ── Inventory ──────────────────────────────────────────────────────
    async def get_inventory(self, user_id: int) -> list[InventoryRow]:
        rows = await self.db.fetchall(
            """
            SELECT i.item_id, i.quantity, s.name, s.category, s.price,
                   s.description, s.effect_type, s.effect_value,
                   s.duration_sec, s.icon
              FROM inventory AS i
              JOIN shop_items AS s ON s.item_id = i.item_id
             WHERE i.user_id = ? AND i.quantity > 0
             ORDER BY s.category, s.name
            """,
            (user_id,),
        )
        return [
            InventoryRow(
                item=ShopItemRow(
                    item_id=row["item_id"],
                    name=row["name"],
                    category=row["category"],
                    price=row["price"],
                    description=row["description"],
                    effect_type=row["effect_type"],
                    effect_value=row["effect_value"],
                    duration_sec=row["duration_sec"],
                    icon=row["icon"],
                ),
                quantity=row["quantity"],
            )
            for row in rows
        ]

    async def get_quantity(self, user_id: int, item_id: str) -> int:
        return int(
            await self.db.fetchval(
                "SELECT quantity FROM inventory WHERE user_id = ? AND item_id = ?",
                (user_id, item_id),
                0,
            )
        )

    async def has_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        return await self.get_quantity(user_id, item_id) >= quantity

    async def add_item(self, user_id: int, item_id: str, quantity: int = 1) -> int:
        if quantity <= 0:
            raise ValueError("quantity > 0 байх ёстой")
        value = await self.db.fetchval_write(
            """
            INSERT INTO inventory (user_id, item_id, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id) DO UPDATE SET
                quantity = quantity + excluded.quantity
            RETURNING quantity
            """,
            (user_id, item_id, quantity),
        )
        if value is None:
            raise RuntimeError("inventory мөр хадгалж чадсангүй")
        return int(value)

    async def remove_item(self, user_id: int, item_id: str, quantity: int = 1) -> bool:
        if quantity <= 0:
            raise ValueError("quantity > 0 байх ёстой")
        affected = await self.db.execute(
            """
            UPDATE inventory
               SET quantity = quantity - ?
             WHERE user_id = ? AND item_id = ? AND quantity >= ?
            """,
            (quantity, user_id, item_id, quantity),
        )
        if affected != 1:
            return False
        await self.db.execute(
            "DELETE FROM inventory WHERE user_id = ? AND item_id = ? AND quantity = 0",
            (user_id, item_id),
        )
        return True

    # ── Effects ────────────────────────────────────────────────────────
    async def add_effect(
        self, user_id: int, effect_type: str, value: float, expires_at: str
    ) -> int:
        value_id = await self.db.fetchval_write(
            """
            INSERT INTO user_effects (user_id, effect_type, value, expires_at)
            VALUES (?, ?, ?, ?)
            RETURNING effect_id
            """,
            (user_id, effect_type, value, expires_at),
        )
        if value_id is None:
            raise RuntimeError("user_effects мөр хадгалж чадсангүй")
        return int(value_id)

    async def active_effects(self, user_id: int) -> list[EffectRow]:
        rows = await self.db.fetchall(
            """
            SELECT effect_id, user_id, effect_type, value, expires_at, created_at
              FROM user_effects
             WHERE user_id = ? AND expires_at > datetime('now')
             ORDER BY expires_at
            """,
            (user_id,),
        )
        return [EffectRow.from_row(row) for row in rows]

    async def effect_value(self, user_id: int, effect_type: str) -> float:
        value = await self.db.fetchval(
            """
            SELECT MAX(value) FROM user_effects
             WHERE user_id = ? AND effect_type = ?
               AND expires_at > datetime('now')
            """,
            (user_id, effect_type),
        )
        return float(value or 0.0)

    async def purge_expired_effects(self) -> int:
        return await self.db.execute(
            "DELETE FROM user_effects WHERE expires_at <= datetime('now')"
        )
