from __future__ import annotations

from datetime import timedelta

import pytest

from core.database import Database
from core.exceptions import UserNotFoundError
from repositories.cooldown_repo import CooldownRepository
from repositories.guild_repo import GuildRepository
from repositories.log_repo import LogRepository
from repositories.shop_repo import ShopItemRow, ShopRepository
from repositories.user_repo import UserRepository
from utils.time_utils import to_db, utcnow


async def test_migration_003_adds_jail_columns_and_lottery(db: Database) -> None:
    user_columns = {
        row["name"] for row in await db.fetchall("PRAGMA table_info(users)")
    }
    assert {"jail_until", "jail_bail_cost"} <= user_columns
    guild_columns = {
        row["name"] for row in await db.fetchall("PRAGMA table_info(guild_settings)")
    }
    assert "log_channel_id" in guild_columns
    assert (
        await db.fetchval(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='lottery_tickets'"
        )
        == 1
    )


async def test_user_repository_atomic_wallet_bank_and_profile(db: Database) -> None:
    repo = UserRepository(db)
    user = await repo.get_or_create(1)
    assert user.wallet == 500

    assert await repo.credit_wallet(1, 250) == 750
    assert await repo.spend_wallet(1, 300) is True
    assert await repo.spend_wallet(1, 9999) is False
    assert (await repo.get(1)).wallet == 450  # type: ignore[union-attr]

    assert await repo.credit_bank(1, 100) == 100
    assert await repo.spend_bank(1, 40) is True
    wallet, bank = await repo.move_to_bank(1, 50)
    assert (wallet, bank) == (400, 110)
    wallet, bank = await repo.move_to_wallet(1, 10)
    assert (wallet, bank) == (410, 100)

    assert await repo.add_xp(1, 25) == 25
    await repo.set_level_xp(1, 2, 5)
    assert await repo.add_casino_net(1, -30) == -30
    await repo.set_daily(1, 3, to_db(utcnow()))
    await repo.set_jail(1, until=to_db(utcnow() + timedelta(minutes=10)), bail_cost=250)
    jailed = await repo.get(1)
    assert jailed and jailed.jail_bail_cost == 250  # type: ignore[union-attr]
    assert jailed and jailed.is_jailed  # type: ignore[union-attr]
    await repo.clear_jail(1)
    assert (await repo.get(1)).jail_until is None  # type: ignore[union-attr]

    await repo.set_title(1, "Cyber Ronin")
    await repo.set_bio(1, "Aether")
    profile = await repo.get(1)
    assert profile and profile.active_title == "Cyber Ronin"  # type: ignore[union-attr]
    assert profile and profile.bio == "Aether"  # type: ignore[union-attr]
    assert profile and profile.level == 2 and profile.xp == 5  # type: ignore[union-attr]


async def test_user_repository_missing_user_errors(db: Database) -> None:
    repo = UserRepository(db)
    with pytest.raises(UserNotFoundError):
        await repo.credit_wallet(999, 1)
    assert await repo.get(999) is None


async def test_shop_inventory_and_effects(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    shop = ShopRepository(db)

    items = await shop.list_items()
    assert len(items) == 6
    assert {item.item_id for item in items} >= {"aether_shield_charm", "xp_potion_2x"}
    assert (await shop.list_items("defense"))[0].category == "defense"

    assert await shop.add_item(1, "xp_potion_2x", 2) == 2
    assert await shop.get_quantity(1, "xp_potion_2x") == 2
    assert await shop.has_item(1, "xp_potion_2x", 2) is True
    assert await shop.remove_item(1, "xp_potion_2x", 1) is True
    assert await shop.get_quantity(1, "xp_potion_2x") == 1
    assert await shop.remove_item(1, "xp_potion_2x", 5) is False
    inventory = await shop.get_inventory(1)
    assert inventory[0].quantity == 1

    expires = to_db(utcnow() + timedelta(minutes=30))
    await shop.add_effect(1, "xp_boost", 2.0, expires)
    assert await shop.effect_value(1, "xp_boost") == pytest.approx(2.0)
    assert len(await shop.active_effects(1)) == 1
    await shop.add_effect(1, "xp_boost", 3.0, to_db(utcnow() - timedelta(minutes=1)))
    assert await shop.effect_value(1, "xp_boost") == pytest.approx(2.0)
    assert await shop.purge_expired_effects() == 1


async def test_shop_repository_upsert_and_delete(db: Database) -> None:
    shop = ShopRepository(db)
    item = ShopItemRow(
        item_id="test_item",
        name="Test",
        category="tool",
        price=100,
        description="test",
        effect_type="tool",
        effect_value=0.0,
        duration_sec=0,
        icon="✦",
    )
    await shop.upsert_item(item)
    assert (await shop.get_item("test_item")).name == "Test"  # type: ignore[union-attr]
    await shop.upsert_item(
        ShopItemRow(
            item_id="test_item",
            name="Test 2",
            category="tool",
            price=200,
            description="test",
            effect_type="tool",
            effect_value=0.0,
            duration_sec=0,
            icon="✦",
        )
    )
    assert (await shop.get_item("test_item")).price == 200  # type: ignore[union-attr]
    assert await shop.delete_item("test_item") is True
    assert await shop.get_item("test_item") is None


async def test_cooldown_repository(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    cooldowns = CooldownRepository(db)

    assert await cooldowns.is_ready(1, "work") is True
    await cooldowns.set_for(1, "work", 60)
    assert await cooldowns.is_ready(1, "work") is False
    assert await cooldowns.remaining(1, "work") > 0
    await cooldowns.set_for(1, "rob", 60)
    assert await cooldowns.clear_many(1, ("work", "rob")) == 2
    assert await cooldowns.is_ready(1, "work") is True


async def test_guild_repository(db: Database) -> None:
    guilds = GuildRepository(db)
    assert await guilds.prefix(None) == "a!"
    row = await guilds.get_or_create(10)
    assert row.prefix == "a!"
    await guilds.set_prefix(10, "?")
    await guilds.set_tax(10, 0.05)
    await guilds.set_log_channel(10, 123)
    row = await guilds.get(10)  # type: ignore[assignment]
    assert row and row.prefix == "?"  # type: ignore[union-attr]
    assert row and row.tax_pct == pytest.approx(0.05)  # type: ignore[union-attr]
    assert row and row.log_channel_id == 123  # type: ignore[union-attr]
    assert await guilds.prefix(10) == "?"
    assert await guilds.tax_pct(10) == pytest.approx(0.05)


async def test_log_repository_records_and_reads(db: Database) -> None:
    users = UserRepository(db)
    await users.get_or_create(1)
    await users.get_or_create(2)
    logs = LogRepository(db)

    tx_id = await logs.record_transaction(1, 100, "work", 600, {"job": "courier"})
    assert tx_id > 0
    assert (await logs.recent_transactions(1))[0].metadata == '{"job":"courier"}'

    await logs.record_casino(1, "coinflip", 100, 192, "win", {"side": "heads"})
    await logs.record_casino(1, "slots", 50, 0, "loss")
    assert await logs.casino_net(1) == 42
    assert len(await logs.recent_casino(1)) == 2

    await logs.record_game(
        "duel", 1, "win", opponent_id=2, reward_coin=100, reward_xp=20
    )
    game = (await logs.recent_games(1))[0]
    assert game.kind == "duel"
    assert game.reward_coin == 100
