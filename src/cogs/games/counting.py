import ast
import asyncio
import logging
import math
import operator
import time
import weakref
from dataclasses import dataclass
from typing import Any

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.ui.setup import (
    ConfirmActionView,
    SetupPanel,
    SetupState,
    disable_setup_panel,
    state_text,
    sync_toggle_button,
)
from src.utils.config_cache import ConfigCache

logger = logging.getLogger(__name__)

# ===== ӨНГӨНҮҮД =====
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

XP_COOLDOWN_SECONDS = 8
SAVE_COST = 500
SHIELD_LEVEL = 30
SHIELD_COOLDOWN_SECONDS = 7 * 24 * 60 * 60
MILESTONE_XP = {
    69: 15,
    100: 25,
    420: 40,
    500: 50,
    777: 75,
    1_000: 100,
    1_337: 125,
    5_000: 250,
}


@dataclass(frozen=True)
class CountingReward:
    base: int
    math_bonus: int
    milestone_bonus: int
    multiplier_percent: int

    @property
    def total(self) -> int:
        return self.base + self.math_bonus + self.milestone_bonus


def counting_xp_base(count: int) -> int:
    if count >= 5_000:
        return 12
    if count >= 1_000:
        return 10
    if count >= 500:
        return 8
    if count >= 100:
        return 6
    return 5


def _participation_multiplier(recent_users: list[int | str]) -> int:
    """Return an integer percent so reward arithmetic stays deterministic."""
    if len(set(recent_users)) >= 3 or len(recent_users) <= 10:
        return 100
    if len(recent_users) < 20:
        return 50
    return 20


def calculate_counting_reward(
    count: int,
    *,
    used_expression: bool,
    recent_users: list[int | str],
    xp_on_cooldown: bool,
) -> CountingReward:
    milestone = MILESTONE_XP.get(count, 0)
    multiplier = _participation_multiplier(recent_users)
    if xp_on_cooldown:
        return CountingReward(0, 0, milestone, multiplier)
    raw_base = counting_xp_base(count)
    scaled_base = max(1, raw_base * multiplier // 100)
    return CountingReward(scaled_base, 3 if used_expression else 0, milestone, multiplier)


def counting_penalty(current_count: int) -> int:
    return min(100, max(5, 5 + max(0, current_count) // 100))


def counting_level(lifetime_xp: int) -> int:
    return math.isqrt(max(0, int(lifetime_xp)) // 100)


def next_counting_level_xp(level: int) -> int:
    return 100 * (max(0, int(level)) + 1) ** 2


def has_weekly_shield(*, level: int, last_used_at: int | None, now: int) -> bool:
    if level < SHIELD_LEVEL:
        return False
    return last_used_at is None or now - int(last_used_at) >= SHIELD_COOLDOWN_SECONDS

# ==================== АЮУЛГҮЙ МАТЕМАТИК БОДОЛТ ====================
ALLOWED_NODES = {
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.USub, ast.UAdd, ast.Load, ast.Expr,
    ast.Name,
}
SAFE_OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
}

def evaluate_expression(expr: str) -> int | float | None:
    try:
        tree = ast.parse(expr.strip(), mode='eval')
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if type(node) not in ALLOWED_NODES:
            return None
        if isinstance(node, ast.Constant) and type(node.value) not in (int, float):
            return None
    if any(isinstance(n, ast.Name) for n in ast.walk(tree)):
        return None
    def _eval(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            if isinstance(node.op, ast.USub): return -operand
            if isinstance(node.op, ast.UAdd): return +operand
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op_type = type(node.op)
            if op_type in SAFE_OPERATORS:
                return SAFE_OPERATORS[op_type](left, right)
        raise ValueError("Дэмжигдэхгүй үйлдэл")
    try:
        result = _eval(tree.body)
        if isinstance(result, (int, float)):
            return result
        return None
    except (ValueError, ZeroDivisionError, TypeError, OverflowError):
        return None

# ==================== МОДАЛ: РОЛЬ ID ОРУУЛАХ ====================
class RoleIDModal(ui.Modal, title="Роль ID оруулах"):
    role_id_input = ui.TextInput(
        label="Ролийн Discord ID",
        placeholder="123456789012345678",
        required=True
    )
    def __init__(self, view, role_type: str):
        super().__init__()
        self.view = view
        self.role_type = role_type  # 'failed', 'reliable', 'save'

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        role_id_str = self.role_id_input.value.strip()
        try:
            role_id = int(role_id_str)
        except ValueError:
            return await interaction.response.send_message("❌ Буруу ID формат.", ephemeral=True)
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Роль олдсонгүй.", ephemeral=True)

        column_map = {
            "failed": "failed_role_id",
            "reliable": "reliable_role_id",
            "level_5": "level_5_role_id",
            "level_20": "level_20_role_id",
            "level_50": "level_50_role_id",
        }
        column = column_map[self.role_type]
        await self.view.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {column: role.id},
        )
        self.view.cog._cfg_cache.invalidate(self.view.guild_id)
        await interaction.response.send_message(f"✅ {role.mention} роль тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)

# ==================== МОДАЛ: АЛБАДМАЛ ТОО ====================
class ForceCountModal(ui.Modal, title="Тооллын утга тогтоох"):
    number_input = ui.TextInput(
        label="Тоо оруулна уу",
        placeholder="Жишээ: 500",
        required=True
    )
    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        if not await self.view.interaction_check(interaction):
            return
        try:
            num = int(self.number_input.value)
            if num < 0:
                return await interaction.response.send_message("❌ Эерэг тоо оруулна уу.", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

        await self.view.cog.update_progress(interaction.guild.id, num, None, 0)
        await interaction.response.send_message(f"✅ Тоолол **{num}** болж тогтоогдлоо.", ephemeral=True)
        await self.view.refresh(interaction)

# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class CountingSetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("❌ Энэ самбар өөр серверийнх байна.", ephemeral=True)
            return False
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator эрх шаардлагатай.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        self.cog._cfg_cache.invalidate(self.guild_id)
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        if self.message is not None:
            await self.message.edit(embed=embed, view=self)
        else:
            logger.warning("Counting setup panel has no bound message in guild %s", self.guild_id)

    def build_embed(self, cfg, guild):
        if cfg is None:
            channel_text = "❌ Сонгогдоогүй"
            enabled = False
            math_mode = False
            delete_msg = False
            failed_role_text = "❌ Тохируулаагүй"
            reliable_role_text = "❌ Тохируулаагүй"
            level_role_texts = ["❌ Тохируулаагүй"] * 3
            high_score = 0
            best_streak = 0
        else:
            channel = guild.get_channel(cfg['channel_id'])
            channel_text = channel.mention if channel else "❌ Устгагдсан"
            enabled = cfg['enabled']
            math_mode = cfg['math_mode']
            delete_msg = cfg['delete_messages']
            failed_role = guild.get_role(cfg['failed_role_id']) if cfg['failed_role_id'] else None
            reliable_role = guild.get_role(cfg['reliable_role_id']) if cfg['reliable_role_id'] else None
            failed_role_text = failed_role.mention if failed_role else "❌ Тохируулаагүй"
            reliable_role_text = reliable_role.mention if reliable_role else "❌ Тохируулаагүй"
            level_role_texts = []
            for key in ("level_5_role_id", "level_20_role_id", "level_50_role_id"):
                role = guild.get_role(cfg[key]) if cfg.get(key) else None
                level_role_texts.append(role.mention if role else "❌ Тохируулаагүй")
            high_score = cfg['high_score']
            best_streak = cfg['best_streak']

        channel_ready = cfg is not None and not channel_text.startswith("❌")
        panel_state = (
            SetupState.READY
            if channel_ready and enabled
            else SetupState.DISABLED
            if channel_ready
            else SetupState.INCOMPLETE
        )
        panel = SetupPanel(
            "Тооллогын удирдлага",
            "Эхлээд суваг сонгоно. Дараа нь дүрэм, роль, одоогийн тоог удирдана.",
            icon="🔢",
            state=panel_state,
            status=(
                "Тооллого ажиллаж байна"
                if channel_ready and enabled
                else "Суваг бэлэн, систем унтраалттай"
                if channel_ready
                else "Тоолох суваг сонгоогүй"
            ),
        )
        panel.section("Үндсэн тохиргоо", [
            f"📍 Суваг  {channel_text}",
            f"🔘 Систем  {state_text(bool(enabled))}",
            f"🧮 Математик илэрхийлэл  {state_text(bool(math_mode))}",
            f"🗑️ Буруу мессеж устгах  {state_text(bool(delete_msg))}",
        ], icon="⚙️")
        panel.section("Ролын шатлал", [
            f"⚠️ Алдаа  {failed_role_text}",
            f"🌟 Найдвартай  {reliable_role_text}",
            f"🌱 Level 5  {level_role_texts[0]}",
            f"🧮 Level 20  {level_role_texts[1]}",
            f"👑 Level 50  {level_role_texts[2]}",
        ], icon="🎭")
        panel.section("Серверийн амжилт", [
            f"🏆 Дээд тоо  **{high_score:,}**",
            f"🔥 Хамгийн урт цуврал  **{best_streak:,}**",
        ], icon="📈")

        sync_toggle_button(
            self.toggle_enabled,
            bool(enabled),
            disable_label="Тооллого унтраах",
            enable_label="Тооллого асаах",
        )
        self.toggle_math.label = f"Math mode: {'асаалттай' if math_mode else 'унтраалттай'}"
        self.toggle_delete.label = f"Устгалт: {'асаалттай' if delete_msg else 'унтраалттай'}"
        return panel.finish("Самбар 10 минут идэвхтэй")

    # ---------- СУВАГ СОНГОХ ----------
    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Тоолох сувгаа сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.bot.db_manager.upsert(
            "counting_config",
            {"guild_id": str(interaction.guild.id), "channel_id": channel.id, "enabled": 1},
            on_conflict="guild_id",
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- ТӨЛӨВ ТОВЧНУУД ----------
    @ui.button(label="Тооллого асаах", style=discord.ButtonStyle.success, emoji="▶️", row=1)
    async def toggle_enabled(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['enabled']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"enabled": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="Math mode: унтраалттай", style=discord.ButtonStyle.secondary, emoji="🧮", row=1)
    async def toggle_math(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['math_mode']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"math_mode": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="Устгалт: унтраалттай", style=discord.ButtonStyle.secondary, emoji="🗑️", row=1)
    async def toggle_delete(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Эхлээд сувгаа сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['delete_messages']
        await self.cog.bot.db_manager.update(
            "counting_config",
            {"guild_id": str(interaction.guild.id)},
            {"delete_messages": int(new_state)},
        )
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- РОЛЬ ТОХИРГОО ----------
    @ui.button(label="⚠️ Алдааны роль", style=discord.ButtonStyle.danger, row=2)
    async def set_failed_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "failed"))

    @ui.button(label="🌟 Найдвартай роль", style=discord.ButtonStyle.success, row=2)
    async def set_reliable_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "reliable"))

    # ---------- БУСАД ҮЙЛДЭЛ ----------
    @ui.button(label="🔢 Тоо тогтоох", style=discord.ButtonStyle.primary, row=3)
    async def force_number(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ForceCountModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🧹 Бүх тохиргоог устгах", style=discord.ButtonStyle.danger, row=3)
    async def reset_config(self, interaction: discord.Interaction, button: ui.Button):
        confirmation = ConfirmActionView(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(
            "⚠️ Тооллогын тохиргоо, одоогийн тоо, streak бүгдийг устгах уу?",
            view=confirmation,
            ephemeral=True,
        )
        timed_out = await confirmation.wait()
        if timed_out or not confirmation.confirmed:
            return await interaction.followup.send("Reset үйлдлийг цуцаллаа.", ephemeral=True)
        await self.cog.bot.db_manager.delete("counting_config", {"guild_id": str(interaction.guild.id)})
        await self.cog.bot.db_manager.delete("counting_progress", {"guild_id": str(interaction.guild.id)})
        self.cog._prog_cache.invalidate(self.guild_id)
        await interaction.followup.send("✅ Бүх тохиргоо устлаа.", ephemeral=True)
        await self.refresh(interaction)

    @ui.button(label="🌱 Level 5 роль", style=discord.ButtonStyle.secondary, row=4)
    async def set_level_5_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "level_5"))

    @ui.button(label="🧮 Level 20 роль", style=discord.ButtonStyle.secondary, row=4)
    async def set_level_20_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "level_20"))

    @ui.button(label="👑 Level 50 роль", style=discord.ButtonStyle.secondary, row=4)
    async def set_level_50_role(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleIDModal(self, "level_50"))

    async def on_timeout(self):
        await disable_setup_panel(self, self.message)

# ==================== ҮНДСЭН COG ====================
class Counting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._cfg_cache = ConfigCache(ttl=15.0, name="counting_config")
        self._prog_cache = ConfigCache(ttl=10.0, name="counting_progress")
        self._guild_locks: weakref.WeakValueDictionary[int, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def _guild_lock(self, guild_id: int) -> asyncio.Lock:
        key = int(guild_id)
        lock = self._guild_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._guild_locks[key] = lock
        return lock

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

    # ---------- DB туслахууд ----------
    async def get_config(self, guild_id: int) -> dict[str, Any]:
        cached = self._cfg_cache.get_cached(guild_id)
        if cached is not None:
            return cached

        async def _load():
            row = await self.bot.db_manager.fetch_safe(
                "counting_config", {"guild_id": str(guild_id)}, single=True
            )
            if not row:
                return None
            return {
                "channel_id": row.get("channel_id"),
                "enabled": bool(row.get("enabled", 1)),
                "delete_messages": bool(row.get("delete_messages", 0)),
                "math_mode": bool(row.get("math_mode", 0)),
                "failed_role_id": row.get("failed_role_id"),
                "reliable_role_id": row.get("reliable_role_id"),
                "save_role_id": row.get("save_role_id"),
                "level_5_role_id": row.get("level_5_role_id"),
                "level_20_role_id": row.get("level_20_role_id"),
                "level_50_role_id": row.get("level_50_role_id"),
                "high_score": row.get("high_score") or 0,
                "best_streak": row.get("best_streak") or 0,
            }

        return await self._cfg_cache.get(guild_id, _load)

    async def get_progress(self, guild_id: int) -> dict[str, Any]:
        cached = self._prog_cache.get_cached(guild_id)
        if cached is not None:
            return cached

        async def _load():
            row = await self.bot.db_manager.fetch_safe(
                "counting_progress", {"guild_id": str(guild_id)}, single=True
            )
            if not row:
                return {"current": 0, "last_user": None, "streak": 0, "recent_users": []}
            recent_users = row.get("recent_users") or []
            if not isinstance(recent_users, list):
                recent_users = []
            return {
                "current": row.get("current_count", 0),
                "last_user": row.get("last_user_id"),
                "streak": row.get("streak", 0),
                "recent_users": recent_users[-20:],
            }

        return await self._prog_cache.get(guild_id, _load)

    async def update_progress(
        self,
        guild_id: int,
        current: int,
        last_user: int | None,
        streak: int,
        recent_users: list[int | str] | None = None,
    ):
        await self.bot.db_manager.upsert(
            "counting_progress",
            {
                "guild_id": str(guild_id),
                "current_count": current,
                "last_user_id": last_user,
                "streak": streak,
                "recent_users": list(recent_users or [])[-20:],
            },
            on_conflict="guild_id",
        )
        self._prog_cache.invalidate(guild_id)

    async def reset_count(self, guild_id: int):
        await self.update_progress(guild_id, 0, None, 0, [])

    async def get_user_stats(self, guild_id: int, user_id: int) -> dict[str, Any]:
        row = await self.bot.db_manager.fetch_one(
            "counting_stats", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return {
            "guild_id": str(guild_id),
            "user_id": str(user_id),
            "correct": int((row or {}).get("correct") or 0),
            "wrong": int((row or {}).get("wrong") or 0),
            "saves": int((row or {}).get("saves") or 0),
            "strikes": int((row or {}).get("strikes") or 0),
            "best_streak": int((row or {}).get("best_streak") or 0),
            "xp_balance": int((row or {}).get("xp_balance") or 0),
            "lifetime_xp": int((row or {}).get("lifetime_xp") or 0),
            "level": int((row or {}).get("level") or 0),
            "save_tokens": int((row or {}).get("save_tokens") or 0),
            "last_xp_at": (row or {}).get("last_xp_at"),
            "shield_used_at": (row or {}).get("shield_used_at"),
        }

    async def record_correct_count(
        self,
        guild_id: int,
        user_id: int,
        *,
        streak: int,
        reward: CountingReward,
        now: int,
    ) -> tuple[dict[str, Any], int]:
        stats = await self.get_user_stats(guild_id, user_id)
        old_level = counting_level(stats["lifetime_xp"])
        stats["correct"] += 1
        stats["best_streak"] = max(stats["best_streak"], streak)
        if reward.total:
            stats["xp_balance"] += reward.total
            stats["lifetime_xp"] += reward.total
            stats["last_xp_at"] = now
        stats["level"] = counting_level(stats["lifetime_xp"])
        await self.bot.db_manager.upsert(
            "counting_stats", stats, on_conflict="guild_id,user_id"
        )
        return stats, max(0, stats["level"] - old_level)

    async def record_failed_count(
        self,
        guild_id: int,
        user_id: int,
        *,
        current_count: int,
        now: int,
    ) -> tuple[str | None, int, dict[str, Any]]:
        stats = await self.get_user_stats(guild_id, user_id)
        stats["wrong"] += 1
        stats["strikes"] += 1
        protection = None
        penalty = 0
        if has_weekly_shield(
            level=counting_level(stats["lifetime_xp"]),
            last_used_at=stats["shield_used_at"],
            now=now,
        ):
            protection = "shield"
            stats["shield_used_at"] = now
        elif stats["save_tokens"] > 0:
            protection = "save"
            stats["save_tokens"] -= 1
            stats["saves"] += 1
        else:
            requested = counting_penalty(current_count)
            penalty = min(stats["xp_balance"], requested)
            stats["xp_balance"] -= penalty
        await self.bot.db_manager.upsert(
            "counting_stats", stats, on_conflict="guild_id,user_id"
        )
        return protection, penalty, stats

    async def grant_level_roles(self, member: discord.Member, level: int, cfg: dict[str, Any]):
        thresholds = (
            (5, cfg.get("level_5_role_id")),
            (20, cfg.get("level_20_role_id")),
            (50, cfg.get("level_50_role_id")),
        )
        roles = []
        for threshold, role_id in thresholds:
            if level < threshold or not role_id:
                continue
            role = member.guild.get_role(int(role_id))
            if role is not None and role not in member.roles:
                roles.append(role)
        if roles:
            try:
                await member.add_roles(*roles, reason=f"Counting Level {level}")
            except discord.HTTPException:
                logger.warning("Could not grant counting level roles", exc_info=True)

    async def update_high_score(self, guild_id: int, new_score: int):
        await self.bot.db_manager.update(
            "counting_config", {"guild_id": str(guild_id)}, {"high_score": new_score}
        )
        self._cfg_cache.invalidate(guild_id)

    async def update_best_streak(self, guild_id: int, new_streak: int):
        await self.bot.db_manager.update(
            "counting_config", {"guild_id": str(guild_id)}, {"best_streak": new_streak}
        )
        self._cfg_cache.invalidate(guild_id)

    async def add_stats(self, guild_id: int, user_id: int, correct: bool, streak: int = 0):
        col = "correct" if correct else "wrong"
        existing = await self.bot.db_manager.fetch_one(
            "counting_stats", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        if existing:
            current = existing.get(col, 0) or 0
            data = {col: current + 1}
            if correct:
                data["best_streak"] = max(existing.get("best_streak", 0) or 0, streak)
            await self.bot.db_manager.update(
                "counting_stats",
                {"guild_id": str(guild_id), "user_id": str(user_id)},
                data,
            )
        else:
            data = {"guild_id": str(guild_id), "user_id": str(user_id), col: 1}
            if correct:
                data["best_streak"] = streak
            await self.bot.db_manager.insert("counting_stats", data)

    async def add_save_stat(self, guild_id: int, user_id: int):
        existing = await self.bot.db_manager.fetch_one(
            "counting_stats", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        if existing:
            await self.bot.db_manager.update(
                "counting_stats",
                {"guild_id": str(guild_id), "user_id": str(user_id)},
                {"saves": (existing.get("saves", 0) or 0) + 1},
            )
        else:
            await self.bot.db_manager.insert("counting_stats", {
                "guild_id": str(guild_id), "user_id": str(user_id), "saves": 1,
            })

    # ========== PUBLIC API: LEADERBOARD ХОЛБОЛТ ==========
    async def get_top_counters(self, guild_id: int, limit=10, offset=0):
        """Хамгийн олон зөв тоолсон хэрэглэгчдийг буцаана (Leaderboard ког ашиглах)."""
        rows = await self.bot.db_manager.fetch_all(
            "counting_stats",
            {"guild_id": str(guild_id)},
            order_by="correct",
            desc=True,
            limit=limit,
            offset=offset,
        )
        return [(int(r["user_id"]), r.get("correct", 0)) for r in rows]

    # ==================== ТООЛЛОГО СОНСОГЧ ====================
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        cfg = await self.get_config(message.guild.id)
        if not cfg or not cfg["enabled"] or message.channel.id != cfg["channel_id"]:
            return

        try:
            content = message.content.strip()
            num = None
            used_expression = False
            try:
                num = int(content)
            except ValueError:
                if cfg["math_mode"]:
                    num = evaluate_expression(content)
                    used_expression = num is not None
                    if num is not None and not isinstance(num, int):
                        num = None
            if num is None or not isinstance(num, int):
                return

            async with self._guild_lock(message.guild.id):
                # Re-read inside the lock: two Discord events can be dispatched
                # before either has persisted the next number.
                self._prog_cache.invalidate(message.guild.id)
                prog = await self.get_progress(message.guild.id)
                expected = int(prog["current"]) + 1
                repeated_user = (
                    prog["last_user"] is not None
                    and int(prog["last_user"]) == message.author.id
                    and int(prog["current"]) != 0
                )
                now = int(time.time())

                if num != expected or repeated_user:
                    protection, penalty, _stats = await self.record_failed_count(
                        message.guild.id,
                        message.author.id,
                        current_count=int(prog["current"]),
                        now=now,
                    )
                    if protection == "shield":
                        title = "🛡️ ДАРХЛАА АЖИЛЛАЛАА"
                        description = (
                            f"{message.author.mention}-ийн 7 хоногийн Shield тооллыг аварлаа.\n"
                            f"Дараагийн тоо: **{expected}**"
                        )
                        color = INFO_COLOR
                    elif protection == "save":
                        title = "🛟 SAVE АЖИЛЛАЛАА"
                        description = (
                            f"{message.author.mention} 1 Save ашиглаж тооллыг аварлаа.\n"
                            f"Дараагийн тоо: **{expected}**"
                        )
                        color = SUCCESS_COLOR
                    else:
                        await self.reset_count(message.guild.id)
                        reason = (
                            "нэг хэрэглэгч дараалж тоолж болохгүй"
                            if repeated_user and num == expected
                            else f"**{expected}** байх ёстой байсан"
                        )
                        title = "❌ ТООЛОЛ ТАСАРЛАА"
                        description = (
                            f"{message.author.mention}: {reason}.\n"
                            f"Тоолол **0** боллоо • XP торгууль: **-{penalty}**"
                        )
                        color = ERROR_COLOR
                    embed = discord.Embed(title=title, description=description, color=color)
                    embed.set_footer(
                        text=f"Дараагийн тоо: {expected if protection else 1}"
                    )
                    await message.channel.send(embed=embed)
                    if cfg["delete_messages"]:
                        try:
                            await message.delete()
                        except discord.HTTPException:
                            logger.warning(
                                "Could not delete failed count in guild %s",
                                message.guild.id,
                                exc_info=True,
                            )
                    if not protection and cfg["failed_role_id"]:
                        role = message.guild.get_role(cfg["failed_role_id"])
                        if role:
                            try:
                                await message.author.add_roles(role, reason="Тооллогын алдаа")
                            except discord.HTTPException:
                                logger.warning(
                                    "Could not grant failed-count role in guild %s",
                                    message.guild.id,
                                    exc_info=True,
                                )
                    return

                recent_users = [*prog.get("recent_users", []), message.author.id][-20:]
                preview = await self.get_user_stats(message.guild.id, message.author.id)
                last_xp_at = preview.get("last_xp_at")
                reward = calculate_counting_reward(
                    expected,
                    used_expression=used_expression,
                    recent_users=recent_users,
                    xp_on_cooldown=(
                        last_xp_at is not None and now - int(last_xp_at) < XP_COOLDOWN_SECONDS
                    ),
                )
                new_streak = int(prog["streak"] or 0) + 1
                await self.update_progress(
                    message.guild.id,
                    expected,
                    message.author.id,
                    new_streak,
                    recent_users,
                )
                stats, levels_gained = await self.record_correct_count(
                    message.guild.id,
                    message.author.id,
                    streak=new_streak,
                    reward=reward,
                    now=now,
                )

                if expected > cfg["high_score"]:
                    await self.update_high_score(message.guild.id, expected)
                if new_streak > cfg["best_streak"]:
                    await self.update_best_streak(message.guild.id, new_streak)

                quests_cog = self.bot.get_cog("Quests")
                if quests_cog:
                    await quests_cog.trigger_event(
                        message.author.id, message.guild.id, "counting_participate", 1
                    )

                try:
                    await message.add_reaction("✅")
                except discord.HTTPException:
                    logger.warning(
                        "Could not react to count in guild %s", message.guild.id, exc_info=True
                    )

                notices = []
                if reward.milestone_bonus:
                    notices.append(
                        f"🎯 **{expected} milestone** • Jackpot **+{reward.milestone_bonus} XP**"
                    )
                if levels_gained:
                    notices.append(f"⬆️ **Counting Level {stats['level']}** хүрлээ")
                    await self.grant_level_roles(message.author, stats["level"], cfg)
                if notices:
                    notices.append(
                        f"Нийт шагнал: **+{reward.total} XP** • Үлдэгдэл: **{stats['xp_balance']} XP**"
                    )
                    await message.channel.send(
                        embed=discord.Embed(
                            title="🏆 ТООЛЛОГЫН ШАГНАЛ",
                            description="\n".join(notices),
                            color=GOLD_COLOR,
                        )
                    )

                if stats["correct"] >= 50 and cfg["reliable_role_id"]:
                    role = message.guild.get_role(cfg["reliable_role_id"])
                    if role and role not in message.author.roles:
                        try:
                            await message.author.add_roles(
                                role, reason="50 зөв тоололт"
                            )
                        except discord.HTTPException:
                            logger.warning(
                                "Could not grant reliable-count role in guild %s",
                                message.guild.id,
                                exc_info=True,
                            )

        except Exception as exc:
            # Protect on_message from transient DB failures per event.
            if getattr(exc, "code", None) in ("42501", "PGRST202", "PGRST205"):
                logger.debug("counting DB unavailable in guild %s: %s", message.guild.id, exc)
            else:
                logger.warning("counting error in guild %s: %s", message.guild.id, exc, exc_info=True)

    # ==================== ХЭРЭГЛЭГЧИЙН КОМАНДУУД ====================
    @commands.command(name="count_stats_user", aliases=["countuser"])
    async def count_stats_user(self, ctx, member: discord.Member | None = None):
        if ctx.guild is None:
            return await ctx.send("❌ Энэ command-ийг серверт ашиглана уу.")
        target = member or ctx.author
        stats = await self.get_user_stats(ctx.guild.id, target.id)
        if not stats["correct"] and not stats["wrong"] and not stats["lifetime_xp"]:
            embed = discord.Embed(
                title="📊 Тооллогын статистик",
                description=f"{target.mention} одоогоор тооллогод оролцоогүй байна.",
                color=INFO_COLOR,
            )
        else:
            correct = stats["correct"]
            wrong = stats["wrong"]
            total = correct + wrong
            accuracy = (correct / total * 100) if total > 0 else 0
            next_xp = next_counting_level_xp(stats["level"])
            shield_ready = has_weekly_shield(
                level=stats["level"],
                last_used_at=stats["shield_used_at"],
                now=int(time.time()),
            )
            embed = discord.Embed(
                title=f"📊 {target.display_name} — Counting Level {stats['level']}",
                description=(
                    f"**XP:** {stats['xp_balance']:,} зарцуулах • "
                    f"{stats['lifetime_xp']:,}/{next_xp:,} нийт"
                ),
                color=INFO_COLOR,
            )
            embed.add_field(name="✅ Зөв", value=f"```{correct}```", inline=True)
            embed.add_field(name="❌ Буруу", value=f"```{wrong}```", inline=True)
            embed.add_field(name="🎯 Нарийвчлал", value=f"```{accuracy:.1f}%```", inline=True)
            embed.add_field(
                name="🛟 Save",
                value=f"```{stats['save_tokens']} үлдсэн / {stats['saves']} ашигласан```",
                inline=True,
            )
            embed.add_field(
                name="⚠️ Анхааруулга", value=f"```{stats['strikes']}```", inline=True
            )
            embed.add_field(
                name="🛡️ Shield",
                value="```Бэлэн```" if shield_ready else "```Цэнэглэгдэж байна```",
                inline=True,
            )
            embed.set_thumbnail(url=target.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="count_stats_server", aliases=["countserver"])
    async def count_stats_server(self, ctx):
        if ctx.guild is None:
            return await ctx.send("❌ Энэ command-ийг серверт ашиглана уу.")
        cfg = await self.get_config(ctx.guild.id)
        if not cfg:
            return await ctx.send("❌ Тохиргоо хийгдээгүй.")
        prog = await self.get_progress(ctx.guild.id)
        embed = discord.Embed(title="📈 СЕРВЕРИЙН ТООЛЛОГО", color=INFO_COLOR)
        embed.add_field(name="🔢 Одоогийн тоо", value=f"```{prog['current']}```", inline=True)
        embed.add_field(name="🏆 Дээд амжилт", value=f"```{cfg['high_score']}```", inline=True)
        embed.add_field(name="🔥 Хамгийн урт цуврал", value=f"```{cfg['best_streak']}```", inline=True)
        embed.add_field(name="👤 Одоогийн цуврал", value=f"```{prog['streak']}```", inline=True)
        embed.add_field(name="📢 Суваг", value=f"<#{cfg['channel_id']}>", inline=True)
        embed.add_field(name="🔘 Төлөв", value="Идэвхтэй" if cfg['enabled'] else "Унтарсан", inline=True)
        embed.add_field(name="🧮 Math Mode", value="Идэвхтэй" if cfg['math_mode'] else "Унтарсан", inline=True)
        embed.add_field(
            name="✨ XP систем",
            value=(
                f"5–12 XP • Math +3 • Save {SAVE_COST} XP\n"
                f"Level {SHIELD_LEVEL}-оос 7 хоногийн Shield"
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    @commands.command(name="count_save", aliases=["countbuy"])
    async def count_save(self, ctx, amount: int = 1):
        if ctx.guild is None:
            return await ctx.send("❌ Энэ command-ийг серверт ашиглана уу.")
        cfg = await self.get_config(ctx.guild.id)
        if not cfg or not cfg["enabled"]:
            return await ctx.send("❌ Тооллого идэвхгүй байна.")
        if not 1 <= amount <= 10:
            return await ctx.send("❌ Нэг удаад 1–10 Save авна уу.")
        cost = SAVE_COST * amount
        async with self._guild_lock(ctx.guild.id):
            stats = await self.get_user_stats(ctx.guild.id, ctx.author.id)
            if stats["xp_balance"] < cost:
                return await ctx.send(
                    f"❌ **{cost:,} XP** хэрэгтэй. Таны үлдэгдэл: **{stats['xp_balance']:,} XP**."
                )
            stats["xp_balance"] -= cost
            stats["save_tokens"] += amount
            await self.bot.db_manager.upsert(
                "counting_stats", stats, on_conflict="guild_id,user_id"
            )
        embed = discord.Embed(
            title="🛟 Save худалдаж авлаа",
            description=(
                f"{ctx.author.mention} **{amount} Save** авлаа.\n"
                f"Зарцуулсан: **{cost:,} XP** • Үлдэгдэл: **{stats['xp_balance']:,} XP**\n"
                "Алдаа гарахад Save автоматаар ашиглагдана."
            ),
            color=SUCCESS_COLOR,
        )
        await ctx.send(embed=embed)

    # ==================== АДМИН ТОХИРГОО (ГАНЦ КОМАНД) ====================
    @app_commands.command(name="counting_setup", description="Тооллогын бүх тохиргоог удирдах самбар")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(administrator=True)
    async def counting_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild.id)
        view = CountingSetupView(self, interaction.guild.id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True, wait=True)

async def setup(bot):
    await bot.add_cog(Counting(bot))
