"""Shop: Merchant's Eye хямдралтай худалдан авалт, title зүүх."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.database import Database
from core.exceptions import (
    InsufficientFundsError,
    ItemNotFoundError,
    ItemNotUsableError,
)
from core.locks import user_lock
from repositories.log_repo import LogRepository
from repositories.shop_repo import InventoryRow, ShopItemRow, ShopRepository
from repositories.user_repo import UserRepository
from services.rpg.skill_service import SkillService
from utils.validators import parse_quantity


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    item: ShopItemRow
    quantity: int
    unit_price: int
    total: int
    wallet: int


class ShopService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        shop: ShopRepository | None = None,
        logs: LogRepository | None = None,
        skills: SkillService | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.shop = shop or ShopRepository(db)
        self.logs = logs or LogRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)

    async def list_items(self, category: str | None = None) -> list[ShopItemRow]:
        return await self.shop.list_items(category)

    async def get_item(self, item_id: str) -> ShopItemRow:
        item = await self.shop.get_item(item_id)
        if item is None:
            raise ItemNotFoundError()
        return item

    async def price_for(self, user_id: int, item: ShopItemRow) -> int:
        mods = await self.skills.get_modifiers(user_id)
        return mods.discounted_price(item.price)

    async def inventory(self, user_id: int) -> list[InventoryRow]:
        return await self.shop.get_inventory(user_id)

    async def buy(
        self, user_id: int, item_id: str, quantity: int | str = 1
    ) -> PurchaseResult:
        count = parse_quantity(quantity, minimum=1, maximum=99)
        async with user_lock(user_id), self.db.transaction():
            user = await self.users.get_or_create(user_id)
            item = await self.shop.get_item(item_id)
            if item is None:
                raise ItemNotFoundError()
            mods = await self.skills.get_modifiers(user_id)
            unit_price = mods.discounted_price(item.price)
            total = unit_price * count
            if not await self.users.spend_wallet(user_id, total):
                raise InsufficientFundsError(
                    f"✦ **{item.name}** ×{count} худалдахад **{total:,}** ⛃ "
                    f"хүрэлцэхгүй (Wallet: **{user.wallet:,}**)."
                )
            await self.shop.add_item(user_id, item.item_id, count)
            wallet = (await self.users.get(user_id)).wallet  # type: ignore[union-attr]
            await self.logs.record_transaction(
                user_id,
                -total,
                "shop_buy",
                wallet,
                {"item": item.item_id, "quantity": count, "unit_price": unit_price},
            )
        return PurchaseResult(
            item=item,
            quantity=count,
            unit_price=unit_price,
            total=total,
            wallet=wallet,
        )

    async def equip_title(self, user_id: int, item_id: str) -> str:
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            item = await self.shop.get_item(item_id)
            if item is None:
                raise ItemNotFoundError()
            if item.category != "title":
                raise ItemNotUsableError("✦ Энэ item нь title биш байна.")
            if not await self.shop.has_item(user_id, item_id):
                raise ItemNotUsableError("✦ Энэ title таны inventory-д байхгүй.")
            await self.users.set_title(user_id, item.name)
        return item.name

    async def grant_item(self, user_id: int, item_id: str, quantity: int = 1) -> None:
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            if await self.shop.get_item(item_id) is None:
                raise ItemNotFoundError()
            await self.shop.add_item(user_id, item_id, quantity)

    async def add_catalog_item(self, item: ShopItemRow) -> None:
        await self.shop.upsert_item(item)

    async def metadata(self, item: ShopItemRow) -> dict[str, Any]:
        return {
            "item_id": item.item_id,
            "name": item.name,
            "price": item.price,
            "category": item.category,
        }
