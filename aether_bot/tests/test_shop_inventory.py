from __future__ import annotations

import pytest

from core.database import Database
from core.exceptions import (
    InsufficientFundsError,
    InsufficientInventoryError,
    InvalidAmountError,
    ItemNotFoundError,
    ItemNotUsableError,
)
from repositories.cooldown_repo import CooldownRepository
from repositories.log_repo import LogRepository
from repositories.shop_repo import ShopRepository
from repositories.skill_repo import SkillRepository
from repositories.user_repo import UserRepository
from services.rpg.inventory_service import InventoryService
from services.rpg.shop_service import ShopService
from services.rpg.skill_service import SkillService


async def test_shop_buy_updates_wallet_inventory_and_log(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.credit_wallet(1, 5_000)
    shop = ShopService(db, users=users)

    result = await shop.buy(1, "xp_potion_2x", 2)
    assert result.quantity == 2
    assert result.unit_price == 900
    assert result.total == 1_800
    assert result.wallet == 3_700
    assert (await shop.inventory(1))[0].quantity == 2

    history = await LogRepository(db).recent_transactions(1)
    assert history[0].source == "shop_buy"
    assert history[0].amount == -1_800

    with pytest.raises(InsufficientFundsError, match="Cyber Ronin"):
        await shop.buy(1, "cyber_ronin_title")
    with pytest.raises(ItemNotFoundError):
        await shop.buy(1, "missing_item")


async def test_shop_quantity_parser_and_maximum(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.credit_wallet(1, 10_000)
    shop = ShopService(db, users=users)

    result = await shop.buy(1, "stamina_elixir", "2")
    assert result.quantity == 2
    assert result.total == 1_200
    with pytest.raises(InvalidAmountError, match="хамгийн ихдээ"):
        await shop.buy(1, "stamina_elixir", 100)


async def test_merchants_eye_discounts_purchase(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.credit_wallet(1, 10_000)
    skills_repo = SkillRepository(db)
    for _ in range(3):
        await skills_repo.increment_level(1, "merchants_eye", 3)
    skills = SkillService(db, user_repo=users)
    shop = ShopService(db, users=users, skills=skills)

    item = await shop.get_item("xp_potion_2x")
    assert await shop.price_for(1, item) == 765
    result = await shop.buy(1, "xp_potion_2x")
    assert result.unit_price == 765
    assert result.wallet == 9_735


async def test_equip_title_requires_title_item(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    shop = ShopService(db, users=users)
    await shop.grant_item(1, "cyber_ronin_title")

    assert await shop.equip_title(1, "cyber_ronin_title") == "Cyber Ronin"
    assert (await users.get(1)).active_title == "Cyber Ronin"  # type: ignore[union-attr]

    await shop.grant_item(1, "xp_potion_2x")
    with pytest.raises(ItemNotUsableError, match="title"):
        await shop.equip_title(1, "xp_potion_2x")
    with pytest.raises(ItemNotFoundError):
        await shop.equip_title(1, "missing_item")


async def test_inventory_shield_and_xp_boost(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    shop = ShopService(db, users=users)
    await shop.grant_item(1, "aether_shield_charm")
    await shop.grant_item(1, "xp_potion_2x")
    inventory = InventoryService(db, users=users)

    shield = await inventory.use(1, "aether_shield_charm")
    assert shield.quantity_left == 0
    assert shield.active_until is not None
    assert (await users.get(1)).shield_until is not None  # type: ignore[union-attr]

    boost = await inventory.use(1, "xp_potion_2x")
    assert boost.quantity_left == 0
    assert await inventory.xp_multiplier(1) == pytest.approx(2.0)
    assert len(await inventory.active_effects(1)) == 1


async def test_inventory_title_and_stamina(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    shop = ShopService(db, users=users)
    await shop.grant_item(1, "astral_princess_title")
    await shop.grant_item(1, "stamina_elixir")
    inventory = InventoryService(db, users=users)

    title = await inventory.use(1, "astral_princess_title")
    assert title.quantity_left == 1  # title нь бүрмөсөн зарцуулагдахгүй
    assert (await users.get(1)).active_title == "Astral Princess"  # type: ignore[union-attr]

    cooldowns = CooldownRepository(db)
    await cooldowns.set_for(1, "work", 600)
    await cooldowns.set_for(1, "rob", 600)
    stamina = await inventory.use(1, "stamina_elixir")
    assert stamina.quantity_left == 0
    assert await cooldowns.is_ready(1, "work")
    assert await cooldowns.is_ready(1, "rob")


async def test_inventory_skill_reset_refunds_sp(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.grant_skill_points(1, 5)
    await users.spend_skill_points(1, 2)
    skills_repo = SkillRepository(db)
    await skills_repo.increment_level(1, "critical_strike", 3)
    await skills_repo.increment_level(1, "critical_strike", 3)
    shop = ShopService(db, users=users)
    await shop.grant_item(1, "skill_reset_tome")

    result = await InventoryService(db, users=users).use(1, "skill_reset_tome")
    assert result.quantity_left == 0
    user = await users.get(1)
    assert user and user.skill_points == 5  # type: ignore[union-attr]
    assert await skills_repo.get_all(1) == {}


async def test_inventory_errors(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    inventory = InventoryService(db, users=users)
    with pytest.raises(ItemNotFoundError):
        await inventory.use(1, "missing_item")
    with pytest.raises(InsufficientInventoryError):
        await inventory.use(1, "aether_shield_charm")


async def test_shop_catalog_admin_helpers(db: Database) -> None:
    shop = ShopRepository(db)
    assert (await shop.get_item("aether_shield_charm")).effect_type == "shield"  # type: ignore[union-attr]
    items = await shop.list_items("booster")
    assert {item.item_id for item in items} == {"xp_potion_2x", "stamina_elixir"}
