"""Inventory: item хэрэглэх (Shield, XP Boost, Skill Reset, Stamina, Title)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from core.database import Database
from core.exceptions import (
    InsufficientInventoryError,
    ItemNotFoundError,
    ItemNotUsableError,
)
from core.locks import user_lock
from repositories.cooldown_repo import CooldownRepository
from repositories.shop_repo import EffectRow, ShopItemRow, ShopRepository
from repositories.user_repo import UserRepository
from services.rpg.skill_service import SkillService
from utils.time_utils import to_db, utcnow


@dataclass(frozen=True, slots=True)
class UseResult:
    item: ShopItemRow
    message: str
    quantity_left: int
    active_until: str | None = None


class InventoryService:
    def __init__(
        self,
        db: Database,
        *,
        users: UserRepository | None = None,
        shop: ShopRepository | None = None,
        cooldowns: CooldownRepository | None = None,
        skills: SkillService | None = None,
    ) -> None:
        self.db = db
        self.users = users or UserRepository(db)
        self.shop = shop or ShopRepository(db)
        self.cooldowns = cooldowns or CooldownRepository(db)
        self.skills = skills or SkillService(db, user_repo=self.users)

    async def inventory(self, user_id: int) -> list:
        return await self.shop.get_inventory(user_id)

    async def active_effects(self, user_id: int) -> list[EffectRow]:
        return await self.shop.active_effects(user_id)

    async def xp_multiplier(self, user_id: int) -> float:
        return max(1.0, await self.shop.effect_value(user_id, "xp_boost"))

    async def use(self, user_id: int, item_id: str) -> UseResult:
        async with user_lock(user_id), self.db.transaction():
            await self.users.get_or_create(user_id)
            item = await self.shop.get_item(item_id)
            if item is None:
                raise ItemNotFoundError()
            if not await self.shop.has_item(user_id, item_id):
                raise InsufficientInventoryError(
                    f"✦ **{item.name}** таны inventory-д байхгүй."
                )

            now = utcnow()
            active_until: str | None = None
            message = f"✦ **{item.name}** ашиглагдлаа."
            remove = True

            if item.effect_type == "shield":
                until = now + timedelta(seconds=max(1, item.duration_sec))
                active_until = to_db(until)
                await self.users.set_shield_until(user_id, active_until)
                message = (
                    f"🛡️ **{item.name}** идэвхжлээ. "
                    f"<t:{int(until.timestamp())}:R> хүртэл хамгаална."
                )
            elif item.effect_type == "xp_boost":
                until = now + timedelta(seconds=max(1, item.duration_sec))
                active_until = to_db(until)
                await self.shop.add_effect(
                    user_id, "xp_boost", item.effect_value or 2.0, active_until
                )
                message = (
                    f"🧪 **{item.name}** идэвхжлээ. XP ×{item.effect_value:g} "
                    f"<t:{int(until.timestamp())}:R> хүртэл."
                )
            elif item.effect_type == "skill_reset":
                reset = await self.skills.reset(user_id)
                message = (
                    f"📜 **{item.name}** ашиглав. "
                    f"**{reset.refunded_points} SP** буцаж, нийт "
                    f"**{reset.skill_points} SP** боллоо."
                )
            elif item.effect_type == "stamina":
                await self.cooldowns.clear_many(user_id, ("work", "rob"))
                message = "⚡ Work болон Rob-ийн cooldown цэвэрлэгдлээ."
            elif item.effect_type == "title":
                await self.users.set_title(user_id, item.name)
                remove = False
                message = f"👑 **{item.name}** цол зүүгдлээ."
            else:
                raise ItemNotUsableError(
                    f"✦ **{item.name}**-ийг одоо ашиглах боломжгүй."
                )

            if remove:
                await self.shop.remove_item(user_id, item_id)
            left = await self.shop.get_quantity(user_id, item_id)

        return UseResult(
            item=item,
            message=message,
            quantity_left=left,
            active_until=active_until,
        )
