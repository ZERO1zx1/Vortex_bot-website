"""Aether-ийн Discord embed туслахууд.

UI давхарга л `discord` импортлоно; service/repository давхарга хэзээ ч
`discord`-ийг мэдэхгүй.
"""

from __future__ import annotations

import random

import discord

import config
from repositories.user_repo import UserRow
from services.rpg.skill_service import Modifiers, SkillTree

BAR_FILLED = "█"
BAR_EMPTY = "░"


def progress_bar(current: int, total: int, *, length: int = 10) -> str:
    """`current/total`-ийг █░ progress bar болгоно (0..length)."""
    if length <= 0:
        return ""
    if total <= 0:
        return BAR_EMPTY * length
    ratio = max(0.0, min(1.0, current / total))
    filled = min(length, max(0, int(ratio * length + 0.5)))
    return BAR_FILLED * filled + BAR_EMPTY * (length - filled)


def format_number(value: int) -> str:
    return f"{value:,}"


def base_embed(
    title: str,
    description: str = "",
    *,
    color: int = config.PRIMARY,
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_author(name=config.BRAND_AUTHOR)
    embed.set_footer(text=random.choice(config.FOOTER_QUOTES))
    return embed


def balance_embed(user: UserRow, mods: Modifiers, display_name: str) -> discord.Embed:
    embed = base_embed(
        f"💠 {display_name} — Aether Wallet",
        "Оддын эдийн засаг дахь таны одоогийн байдал.",
    )
    embed.add_field(
        name="👛 Wallet", value=f"**{format_number(user.wallet)}** ⛃", inline=True
    )
    embed.add_field(
        name="🏦 Bank", value=f"**{format_number(user.bank)}** ⛃", inline=True
    )
    embed.add_field(
        name="📈 Net worth",
        value=f"**{format_number(user.net_worth)}** ⛃",
        inline=True,
    )
    embed.add_field(
        name="⚡ Level / XP",
        value=f"**Lv.{user.level}** · {format_number(user.xp)} XP",
        inline=True,
    )
    embed.add_field(
        name="✨ Skill points",
        value=f"**{user.skill_points}** SP",
        inline=True,
    )
    embed.add_field(
        name="🎖️ Title",
        value=user.active_title or "Wanderer",
        inline=True,
    )
    if mods.work_income_mult > 1.0:
        bonus = (mods.work_income_mult - 1.0) * 100
        embed.add_field(name="🪙 Income bonus", value=f"+{bonus:.1f}%", inline=True)
    if mods.shield_active:
        embed.add_field(name="🛡️ Shield", value="Идэвхтэй", inline=True)
    return embed


def skills_embed(tree: SkillTree) -> discord.Embed:
    embed = base_embed(
        "🌌 Skill Tree",
        f"**Lv.{tree.level}** · **{tree.skill_points} SP** · "
        f"Нийт **{tree.total_levels}** түвшин",
        color=config.CYAN,
    )
    for path_id, states in tree.paths.items():
        lines: list[str] = []
        for state in states:
            skill = state.skill
            if state.level <= 0:
                status = f"🔒 Lv.{skill.unlock_level}"
            elif state.is_active:
                status = "✨ Идэвхтэй"
            elif state.cooldown_remaining:
                status = f"⏳ {state.cooldown_remaining}с"
            else:
                status = "✅"
            lines.append(
                f"{skill.icon} **{skill.name}** — `{state.level}/{skill.max_level}` {status}"
            )
        embed.add_field(
            name=f"{config.SEPARATOR} {path_id.title()}",
            value="\n".join(lines),
            inline=False,
        )
    return embed
