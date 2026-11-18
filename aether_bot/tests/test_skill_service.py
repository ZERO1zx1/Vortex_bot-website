from __future__ import annotations

import pytest

from core.database import Database
from core.exceptions import (
    CooldownError,
    SkillLockedError,
    SkillNotActiveTypeError,
    SkillNotFoundError,
)
from services.rpg.skill_service import Modifiers, SkillService


async def test_skill_upgrade_modifiers_activation_and_reset(db: Database) -> None:
    service = SkillService(db, cache_ttl=0.0)
    await db.execute(
        "INSERT INTO users (user_id, wallet, level, skill_points) "
        "VALUES (1, 500, 10, 5)"
    )

    first = await service.upgrade(1, "golden_touch")
    second = await service.upgrade(1, "golden_touch")
    mods = await service.get_modifiers(1)
    assert (first.new_level, second.new_level) == (1, 2)
    assert mods.work_income_mult == pytest.approx(1.12)

    await service.upgrade(1, "aether_shield")
    activation = await service.activate(1, "aether_shield")
    assert activation.skill.skill_id == "aether_shield"
    assert (await service.get_modifiers(1)).shield_active is True

    with pytest.raises(CooldownError):
        await service.activate(1, "aether_shield")

    assert await service.consume_charge(1, "aether_shield") is True
    assert (await service.get_modifiers(1)).shield_active is False

    reset = await service.reset(1)
    assert reset.refunded_points == 3
    assert reset.skill_points == 5


def test_reward_rounding_is_half_up() -> None:
    mods = Modifiers(
        work_income_mult=1.25,
        xp_gain_mult=1.25,
        shop_discount_pct=0.5,
        casino_cashback_pct=0.5,
    )
    assert mods.apply_income(2) == 3
    assert mods.apply_xp(2) == 3
    assert mods.discounted_price(5) == 2
    assert mods.cashback(5) == 3


async def test_shadow_step_fine_reduction_comes_from_catalog(db: Database) -> None:
    service = SkillService(db, cache_ttl=0.0)
    await db.execute(
        "INSERT INTO users (user_id, wallet, level, skill_points) "
        "VALUES (2, 500, 10, 5)"
    )
    for _ in range(5):
        await service.upgrade(2, "shadow_step")
    mods = await service.get_modifiers(2)
    assert mods.rob_success_bonus == pytest.approx(0.20)
    assert mods.rob_fine_mult == pytest.approx(0.75)


async def test_activate_rechecks_unlock_level(db: Database) -> None:
    service = SkillService(db, cache_ttl=0.0)
    await db.execute("INSERT INTO users (user_id, wallet, level) VALUES (3, 500, 1)")
    await db.execute(
        "INSERT INTO user_skills (user_id, skill_id, skill_level) "
        "VALUES (3, 'aether_shield', 1)"
    )
    with pytest.raises(SkillLockedError):
        await service.activate(3, "aether_shield")


async def test_consume_charge_validates_skill_type(db: Database) -> None:
    service = SkillService(db, cache_ttl=0.0)
    with pytest.raises(SkillNotFoundError):
        await service.consume_charge(1, "missing")
    with pytest.raises(SkillNotActiveTypeError):
        await service.consume_charge(1, "golden_touch")


async def test_get_tree_creates_user_at_command_boundary(db: Database) -> None:
    service = SkillService(db, cache_ttl=0.0)
    tree = await service.get_tree(42)
    assert tree.user_id == 42
    assert tree.skill_points == 0
    assert await db.fetchval("SELECT wallet FROM users WHERE user_id = 42") == 500


async def test_modifier_cache_is_not_poisoned_by_rollback(db: Database) -> None:
    service = SkillService(db, cache_ttl=60.0)
    await db.execute("INSERT INTO users (user_id, wallet) VALUES (7, 500)")
    assert (await service.get_modifiers(7)).work_income_mult == pytest.approx(1.0)

    with pytest.raises(RuntimeError, match="rollback"):
        async with db.transaction():
            await db.execute(
                "INSERT INTO user_skills (user_id, skill_id, skill_level) "
                "VALUES (7, 'golden_touch', 5)"
            )
            inside = await service.get_modifiers(7)
            assert inside.work_income_mult == pytest.approx(1.3)
            raise RuntimeError("rollback")

    after = await service.get_modifiers(7)
    assert after.work_income_mult == pytest.approx(1.0)
