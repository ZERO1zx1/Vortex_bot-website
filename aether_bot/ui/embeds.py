"""Aether-ийн Discord embed туслахууд.

UI давхарга л `discord` импортлоно; service/repository давхарга хэзээ ч
`discord`-ийг мэдэхгүй.
"""

from __future__ import annotations

import random

import discord

import config
from core.skill_catalog import PATHS
from repositories.shop_repo import EffectRow, InventoryRow, ShopItemRow
from repositories.user_repo import UserRow
from services.casino.base import CasinoResult
from services.casino.blackjack_service import BlackjackState
from services.casino.crash_service import CrashState
from services.casino.lottery_service import LotteryDraw, LotteryInfo
from services.casino.minefield_service import MinefieldState
from services.economy.crime_service import CrimeResult, RobResult
from services.economy.income_service import DailyResult, WorkResult
from services.economy.jail_service import JailStatus
from services.economy.wallet_service import (
    DepositResult,
    TransferResult,
    WithdrawResult,
)
from services.games.adventure_service import AdventureResult
from services.games.boss_service import BossAttack, BossStatus
from services.games.duel_service import DuelState
from services.games.hunt_fish_service import CatchResult
from services.rpg.inventory_service import UseResult
from services.rpg.level_service import LevelProgress
from services.rpg.shop_service import PurchaseResult
from services.rpg.skill_service import Modifiers, SkillTree
from utils.time_utils import humanize_seconds

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
        path = PATHS.get(path_id)
        title = f"{path.icon} {path.name}" if path else path_id.title()
        embed.add_field(
            name=f"{config.SEPARATOR} {title}",
            value="\n".join(lines),
            inline=False,
        )
    return embed


# ════════════════════════════════════════════════════════════════════════════
# Phase 4 — модуль бүрийн Anime / Cyber-Fantasy embed-үүд
# ════════════════════════════════════════════════════════════════════════════
def _outcome_color(outcome: str) -> int:
    return (
        config.SUCCESS
        if outcome in {"win", "cashout", "auto_cashout", "blackjack", "push"}
        else config.DANGER
    )


def _result_core(
    embed: discord.Embed, result: CasinoResult, *, name: str
) -> discord.Embed:
    embed.add_field(name="🎯 Бооцоо", value=f"**{format_number(result.bet)}** ⛃")
    embed.add_field(name="💠 Payout", value=f"**{format_number(result.payout)}** ⛃")
    net_sign = "+" if result.net >= 0 else ""
    embed.add_field(name="📈 Net", value=f"**{net_sign}{format_number(result.net)}** ⛃")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    if result.cashback:
        embed.add_field(
            name="⭐ Lucky Star", value=f"+{format_number(result.cashback)} ⛃"
        )
    embed.set_footer(text=f"✦ Aether System • {name} • +{result.xp} XP")
    return embed


def start_casino_embed(game: str, display_name: str) -> discord.Embed:
    return base_embed(
        f"{game.upper()} — Aether Casino",
        f"Бооцогоо тавих товчоор бооцоогоо тавина (`a!{game} <Бооцоо>`).",
        color=0xFFD700,
    )


def daily_embed(result: DailyResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        f"🌙 {display_name} — Daily Blessing",
        "Оддын систем танд өнөөдрийн хишигээ өглөө.",
        color=config.SUCCESS,
    )
    embed.add_field(name="🪙 Reward", value=f"**{format_number(result.reward)}** ⛃")
    embed.add_field(name="🔥 Streak", value=f"**{result.streak}** өдөр")
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(name="⚡ Level", value=f"**Lv.{result.level}**")
    return embed


def work_embed(result: WorkResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        f"💼 {display_name} — {result.job.icon} {result.job.name}",
        result.job.description or "Aether хотын неон гэрэл дор ажиллалаа.",
        color=config.CYAN,
    )
    embed.add_field(name="🪙 Цалин", value=f"**{format_number(result.reward)}** ⛃")
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(
        name="⏳ Дараагийн ажил",
        value=f"`{humanize_seconds(result.cooldown_sec)}` дараа",
    )
    return embed


def crime_embed(result: CrimeResult, display_name: str) -> discord.Embed:
    color = config.SUCCESS if result.success else config.DANGER
    title = (
        f"🕶️ {result.crime.icon} {result.crime.name} — Амжилттай"
        if result.success
        else f"🚨 {result.crime.icon} {result.crime.name} — Баригдлаа"
    )
    embed = base_embed(title, result.crime.description, color=color)
    if result.success:
        embed.add_field(name="🪙 Олз", value=f"**{format_number(result.reward)}** ⛃")
    else:
        embed.add_field(name="💸 Торгууль", value=f"**{format_number(result.fine)}** ⛃")
        if result.jailed:
            embed.add_field(name="⛓️ Шорон", value="Та хоригдлоо. `a!bail`-аар гарна.")
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.set_footer(text=f"✦ Aether System • {display_name}")
    return embed


def rob_embed(result: RobResult, actor_name: str, target_name: str) -> discord.Embed:
    color = config.SUCCESS if result.success else config.DANGER
    title = (
        f"🌑 {actor_name} → {target_name} — Амжилттай дээрэм"
        if result.success
        else f"🚨 {actor_name} → {target_name} — Баригдлаа"
    )
    embed = base_embed(title, color=color)
    if result.success:
        embed.add_field(
            name="🪙 Хулгайлсан", value=f"**{format_number(result.stolen)}** ⛃"
        )
    else:
        embed.add_field(name="💸 Торгууль", value=f"**{format_number(result.fine)}** ⛃")
        if result.jailed:
            embed.add_field(name="⛓️ Шорон", value="`a!bail`-аар гарна.")
    embed.add_field(
        name="👛 Actor Wallet", value=f"**{format_number(result.actor_wallet)}** ⛃"
    )
    embed.add_field(
        name="👛 Target Wallet", value=f"**{format_number(result.target_wallet)}** ⛃"
    )
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    return embed


def jail_embed(status: JailStatus, display_name: str) -> discord.Embed:
    if not status.jailed:
        return base_embed(
            f"🕊️ {display_name} — Чөлөөтэй",
            "Та одоогоор шоронд биш байна.",
            color=config.SUCCESS,
        )
    embed = base_embed(
        f"⛓️ {display_name} — Aether Шорон",
        "Сүүдрийн хязгаар таныг хүлээж байна.",
        color=config.DANGER,
    )
    embed.add_field(
        name="⏳ Үлдсэн", value=f"`{humanize_seconds(status.remaining_sec)}`"
    )
    embed.add_field(
        name="💰 Батлан даалт", value=f"**{format_number(status.bail_cost)}** ⛃"
    )
    embed.set_footer(text="✦ Aether System • a!bail — гарц нээх")
    return embed


def profile_embed(
    user: UserRow,
    mods: Modifiers,
    progress: LevelProgress,
    display_name: str,
) -> discord.Embed:
    embed = base_embed(
        f"🌌 {display_name} — Aether Profile",
        user.bio or "Aether ертөнцийн аялагч.",
        color=config.PRIMARY,
    )
    embed.add_field(name="👛 Wallet", value=f"**{format_number(user.wallet)}** ⛃")
    embed.add_field(name="🏦 Bank", value=f"**{format_number(user.bank)}** ⛃")
    embed.add_field(name="📈 Net worth", value=f"**{format_number(user.net_worth)}** ⛃")
    embed.add_field(
        name=f"⚡ Level {progress.level}",
        value=f"{progress_bar(progress.xp, progress.required_xp)} "
        f"`{format_number(progress.xp)}/{format_number(progress.required_xp)}`",
        inline=False,
    )
    embed.add_field(name="✨ SP", value=f"**{user.skill_points}**")
    embed.add_field(name="🎖️ Title", value=user.active_title or "Wanderer")
    embed.add_field(
        name="🎰 Casino net",
        value=f"**{format_number(user.casino_net)}** ⛃",
    )
    if mods.work_income_mult > 1.0:
        embed.add_field(
            name="🪙 Income",
            value=f"+{(mods.work_income_mult - 1.0) * 100:.0f}%",
        )
    if mods.casino_cashback_pct:
        embed.add_field(
            name="⭐ Cashback", value=f"{mods.casino_cashback_pct * 100:.0f}%"
        )
    if mods.shield_active:
        embed.add_field(name="🛡️ Shield", value="Идэвхтэй")
    return embed


def deposit_embed(result: DepositResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        "📥 Aether Deposit",
        f"**{format_number(result.amount)}** ⛃ банкинд шилжлээ.",
        color=config.SUCCESS,
    )
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(name="🏦 Bank", value=f"**{format_number(result.bank)}** ⛃")
    embed.set_footer(text=f"✦ Aether System • {display_name}")
    return embed


def withdraw_embed(result: WithdrawResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        "📤 Aether Withdraw",
        f"**{format_number(result.amount)}** ⛃ Wallet руу буцлаа.",
        color=config.CYAN,
    )
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(name="🏦 Bank", value=f"**{format_number(result.bank)}** ⛃")
    embed.set_footer(text=f"✦ Aether System • {display_name}")
    return embed


def transfer_embed(
    result: TransferResult, display_name: str, recipient_id: int | None = None
) -> discord.Embed:
    embed = base_embed(
        "💸 Aether Transfer",
        (
            f"<@{recipient_id}> руу **{format_number(result.net)}** ⛃ илгээгдлээ."
            if recipient_id is not None
            else f"Дүн **{format_number(result.amount)}** ⛃."
        ),
        color=config.SUCCESS,
    )
    if result.tax:
        embed.add_field(name="🏛️ Tax", value=f"**{format_number(result.tax)}** ⛃")
    embed.add_field(
        name="👛 Wallet", value=f"**{format_number(result.sender_wallet)}** ⛃"
    )
    embed.add_field(
        name="💶 Recipient",
        value=f"**{format_number(result.recipient_wallet)}** ⛃",
    )
    embed.set_footer(text=f"✦ Aether System • {display_name}")
    return embed


def shop_embed(
    items: list[ShopItemRow], wallet: int, category: str | None
) -> discord.Embed:
    title = "🛒 Aether Shop"
    if category:
        title += f" — {category.title()}"
    embed = base_embed(
        title,
        "Оддын зах дээрх домогт эд зүйлс. `a!buy <item_id> [тоо]`.",
        color=config.GOLD,
    )
    for item in items[:20]:
        effect = f" · {item.effect_type}"
        if item.effect_value:
            effect += f" ×{item.effect_value:g}"
        embed.add_field(
            name=f"{item.icon} {item.name} — {format_number(item.price)} ⛃",
            value=f"`{item.item_id}`{effect}\n{item.description[:80]}",
            inline=False,
        )
    embed.set_footer(text=f"✦ Aether System • Wallet: {format_number(wallet)} ⛃")
    return embed


def inventory_embed(
    rows: list[InventoryRow], effects: list[EffectRow], display_name: str
) -> discord.Embed:
    embed = base_embed(
        f"🎒 {display_name} — Inventory",
        "Танд байгаа эд зүйлс болон идэвхтэй эффектүүд.",
        color=config.CYAN,
    )
    if not rows:
        embed.add_field(
            name="Хоосон", value="`a!shop`-оос эд зүйл худалдаж авна уу.", inline=False
        )
    for row in rows[:20]:
        embed.add_field(
            name=f"{row.item.icon} {row.item.name} ×{row.quantity}",
            value=f"`{row.item.item_id}` · {row.item.description[:70]}",
            inline=False,
        )
    if effects:
        lines = [
            f"🧪 **{effect.effect_type}** ×{effect.value:g} · <t:{_ts(effect.expires_at)}:R>"
            for effect in effects
        ]
        embed.add_field(name="Идэвхтэй эффект", value="\n".join(lines), inline=False)
    return embed


def _ts(value: str) -> int:
    from utils.time_utils import from_db

    moment = from_db(value)
    return int(moment.timestamp()) if moment else 0


def purchase_embed(result: PurchaseResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        f"🛍️ {display_name} — Худалдан авалт",
        f"**{result.item.icon} {result.item.name}** ×{result.quantity}",
        color=config.SUCCESS,
    )
    embed.add_field(name="💸 Нийт", value=f"**{format_number(result.total)}** ⛃")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(
        name="🎁 Нэгж үнэ", value=f"**{format_number(result.unit_price)}** ⛃"
    )
    return embed


def use_item_embed(result: UseResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        f"✨ {display_name} — {result.item.icon} {result.item.name}",
        result.message,
        color=config.SUCCESS,
    )
    embed.add_field(name="📦 Үлдсэн", value=f"**{result.quantity_left}**")
    return embed


def slots_embed(result: CasinoResult, display_name: str) -> discord.Embed:
    embed = base_embed(
        "🎰 Aether Slots",
        "\n".join(" ".join(row) for row in result.detail.get("grid", [])),
        color=_outcome_color(result.outcome),
    )
    lines = result.detail.get("lines", [])
    if lines:
        wins = "\n".join(
            f"{line['symbol']} ×{line['multiplier']} → +{format_number(line['amount'])} ⛃"
            for line in lines
        )
    else:
        wins = "Шугам таарсангүй."
    embed.add_field(name="📜 Шугамууд", value=wins, inline=False)
    return _result_core(embed, result, name=display_name)


def coinflip_embed(result: CasinoResult, display_name: str) -> discord.Embed:
    landed = result.detail.get("landed", "?")
    icon = "🪙" if landed == "heads" else "🌑"
    embed = base_embed(
        "🪙 Aether Coinflip",
        f"{icon} **{landed}** — {'хожлоо' if result.outcome == 'win' else 'хожигдлоо'}",
        color=_outcome_color(result.outcome),
    )
    embed.add_field(name="Таны сонголт", value=str(result.detail.get("choice", "?")))
    return _result_core(embed, result, name=display_name)


def roulette_embed(result: CasinoResult, display_name: str) -> discord.Embed:
    landed = result.detail.get("landed", "?")
    color = result.detail.get("color", "green")
    color_icon = {"red": "🔴", "black": "⚫", "green": "🟢"}.get(color, "⚪")
    embed = base_embed(
        "🎡 Aether Roulette",
        f"{color_icon} **{landed}** ({color})",
        color=_outcome_color(result.outcome),
    )
    embed.add_field(
        name="Таны бооцоо",
        value=f"{result.detail.get('bet_type', '?')} "
        f"{result.detail.get('picked') if result.detail.get('picked') is not None else ''}",
    )
    return _result_core(embed, result, name=display_name)


def blackjack_embed(state: BlackjackState, display_name: str) -> discord.Embed:
    dealer = " ".join(state.dealer_cards) or "—"
    player = " ".join(state.player_cards) or "—"
    color = (
        config.SUCCESS
        if state.outcome in {"win", "push", "blackjack"}
        else config.DANGER
        if state.outcome in {"loss", "bust"}
        else config.PRIMARY
    )
    embed = base_embed(
        f"🃏 {display_name} — Blackjack",
        f"**Таны гар:** {player} · **{state.player_total}**\n"
        f"**Dealer:** {dealer} · **{state.dealer_total if state.dealer_total is not None else '?'}**",
        color=color,
    )
    embed.add_field(name="🎯 Бооцоо", value=f"**{format_number(state.bet)}** ⛃")
    if state.status == "done":
        net_sign = "+" if state.net >= 0 else ""
        embed.add_field(
            name="📈 Net", value=f"**{net_sign}{format_number(state.net)}** ⛃"
        )
        embed.add_field(name="💠 Payout", value=f"**{format_number(state.payout)}** ⛃")
        embed.add_field(name="👛 Wallet", value=f"**{format_number(state.wallet)}** ⛃")
        if state.cashback:
            embed.add_field(
                name="⭐ Lucky Star", value=f"+{format_number(state.cashback)} ⛃"
            )
        embed.set_footer(text="✦ Aether System • a!bj <bet> — дахин тоглох")
    else:
        embed.set_footer(text="✦ Hit / Stand / Double — зөвхөн таны ээлж")
    return embed


def minefield_embed(state: MinefieldState, display_name: str) -> discord.Embed:
    tiles: list[str] = []
    for row in range(4):
        line = []
        for col in range(4):
            index = row * 4 + col
            if index in state.revealed:
                line.append("💎")
            elif index in state.bombs:
                line.append("💥")
            elif state.active:
                line.append("⬜")
            else:
                line.append("⬛")
        tiles.append(" ".join(line))
    color = (
        config.SUCCESS
        if state.outcome in {"cashout", "auto_cashout"}
        else config.DANGER
        if state.outcome == "loss"
        else config.PRIMARY
    )
    embed = base_embed(
        f"💣 {display_name} — Minefield",
        "\n".join(tiles),
        color=color,
    )
    embed.add_field(name="🎯 Бооцоо", value=f"**{format_number(state.bet)}** ⛃")
    embed.add_field(name="📊 Үржүүлэгч", value=f"**×{state.multiplier:.2f}**")
    embed.add_field(name="💣 Бөмбөг", value=f"**{state.mines_total}**")
    if not state.active:
        net_sign = "+" if state.net >= 0 else ""
        embed.add_field(name="💠 Payout", value=f"**{format_number(state.payout)}** ⛃")
        embed.add_field(
            name="📈 Net", value=f"**{net_sign}{format_number(state.net)}** ⛃"
        )
        embed.add_field(name="👛 Wallet", value=f"**{format_number(state.wallet)}** ⛃")
        if state.cashback:
            embed.add_field(
                name="⭐ Lucky Star", value=f"+{format_number(state.cashback)} ⛃"
            )
    return embed


def crash_embed(state: CrashState, display_name: str) -> discord.Embed:
    if state.active:
        return base_embed(
            f"🚀 {display_name} — Crash ×{state.multiplier:.2f}",
            "Үржүүлэгч өсөж байна. Cashout дарж хожилоо авна уу.\n"
            "**Анхаар:** хэт удвал систем дэлбэрнэ.",
            color=config.CYAN,
        ).add_field(name="🎯 Бооцоо", value=f"**{format_number(state.bet)}** ⛃")
    color = config.SUCCESS if state.outcome == "cashout" else config.DANGER
    embed = base_embed(
        f"💥 {display_name} — Crash ×{state.multiplier:.2f}",
        f"Crash point: **×{state.crash_point:.2f}**",
        color=color,
    )
    embed.add_field(name="🎯 Бооцоо", value=f"**{format_number(state.bet)}** ⛃")
    embed.add_field(name="💠 Payout", value=f"**{format_number(state.payout)}** ⛃")
    net_sign = "+" if state.net >= 0 else ""
    embed.add_field(name="📈 Net", value=f"**{net_sign}{format_number(state.net)}** ⛃")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(state.wallet)}** ⛃")
    if state.cashback:
        embed.add_field(
            name="⭐ Lucky Star", value=f"+{format_number(state.cashback)} ⛃"
        )
    return embed


def lottery_embed(info: LotteryInfo, display_name: str) -> discord.Embed:
    embed = base_embed(
        "🎟️ Aether Lottery",
        f"Round **#{info.round_id}** — Jackpot-ийг хүлээж байна.",
        color=config.GOLD,
    )
    embed.add_field(name="🎫 Тасалбар", value=f"**{info.tickets}**")
    embed.add_field(name="👥 Тоглогчид", value=f"**{len(info.participants)}**")
    embed.add_field(name="💰 Pot", value=f"**{format_number(info.pot)}** ⛃")
    embed.add_field(name="🏷️ Үнэ", value=f"**{format_number(info.price)}** ⛃ / тасалбар")
    embed.add_field(
        name="📜 Дүрэм",
        value=f"Нэг хүн дээд тал нь **{info.max_per_user}** тасалбар. "
        "Ялагч pot-ийн **96%**-ийг авна.",
        inline=False,
    )
    embed.set_footer(text=f"✦ Aether System • {display_name}")
    return embed


def lottery_draw_embed(draw: LotteryDraw) -> discord.Embed:
    embed = base_embed(
        "🎉 Aether Lottery — Сугалаа",
        f"Round **#{draw.round_id}** дууслаа. <@{draw.winner_id}> Jackpot хожлоо!",
        color=config.GOLD,
    )
    embed.add_field(name="🎫 Тасалбар", value=f"**{draw.tickets}**")
    embed.add_field(name="💰 Pot", value=f"**{format_number(draw.pot)}** ⛃")
    embed.add_field(name="💠 Payout", value=f"**{format_number(draw.payout)}** ⛃")
    return embed


def adventure_embed(result: AdventureResult, display_name: str) -> discord.Embed:
    color = config.SUCCESS if result.success else config.DANGER
    embed = base_embed(
        f"🗺️ {display_name} — {result.dungeon.icon} {result.dungeon.name}",
        result.message,
        color=color,
    )
    if result.success:
        embed.add_field(name="🪙 Олз", value=f"**{format_number(result.reward)}** ⛃")
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(
        name="⏳ Cooldown",
        value=f"`{humanize_seconds(result.cooldown_sec)}`",
        inline=False,
    )
    return embed


def catch_embed(result: CatchResult, display_name: str) -> discord.Embed:
    verb = "Ан хийсэн" if result.kind == "hunt" else "Загас барьсан"
    embed = base_embed(
        f"{result.icon} {display_name} — {verb}",
        f"**{result.catch}** олзлов.",
        color=config.SUCCESS,
    )
    embed.add_field(name="🪙 Reward", value=f"**{format_number(result.reward)}** ⛃")
    embed.add_field(name="✨ XP", value=f"**+{result.xp}**")
    embed.add_field(name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃")
    embed.add_field(
        name="⏳ Cooldown",
        value=f"`{humanize_seconds(result.cooldown_sec)}`",
        inline=False,
    )
    return embed


def boss_status_embed(status: BossStatus) -> discord.Embed:
    embed = base_embed(
        f"👹 {status.boss.icon} {status.boss.name}",
        status.boss.description,
        color=config.DANGER,
    )
    embed.add_field(
        name="❤️ HP",
        value=f"{progress_bar(status.hp, status.max_hp)} "
        f"`{format_number(status.hp)}/{format_number(status.max_hp)}`",
        inline=False,
    )
    embed.add_field(
        name="🪙 Kill reward", value=f"**{format_number(status.boss.coin_reward)}** ⛃"
    )
    embed.add_field(name="✨ XP", value=f"**{status.boss.xp_reward}**")
    embed.add_field(name="⚔️ Attack", value=f"**{status.boss.attack}**")
    return embed


def boss_attack_embed(attack: BossAttack, display_name: str) -> discord.Embed:
    color = config.SUCCESS if attack.killed else config.CYAN
    embed = base_embed(
        f"⚔️ {display_name} → {attack.boss.icon} {attack.boss.name}",
        f"**{format_number(attack.damage)}** damage"
        + (" · **CRITICAL!**" if attack.critical else ""),
        color=color,
    )
    embed.add_field(
        name="❤️ HP үлдсэн",
        value=f"**{format_number(attack.hp_left)}** / {format_number(attack.boss.hp)}",
    )
    if attack.killed:
        embed.add_field(
            name="🏆 Kill reward", value=f"**{format_number(attack.reward)}** ⛃"
        )
        embed.add_field(name="👛 Wallet", value=f"**{format_number(attack.wallet)}** ⛃")
    embed.add_field(name="✨ XP", value=f"**+{attack.xp}**")
    return embed


def duel_embed(state: DuelState, challenger: str, opponent: str) -> discord.Embed:
    if state.status == "pending":
        return base_embed(
            "⚔️ Aether Duel — Урилга",
            f"**{challenger}** → **{opponent}**\n"
            f"Бооцоо: **{format_number(state.bet)}** ⛃\n\n"
            f"<@{state.opponent_id}> хүлээн авах эсвэл татгалзана уу.",
            color=config.GOLD,
        )
    if state.status == "declined":
        return base_embed(
            "✖️ Aether Duel — Татгалзсан",
            "Урилга цуцлагдлаа.",
            color=config.MUTED,
        )
    color = config.SUCCESS if state.status == "done" else config.PRIMARY
    embed = base_embed(
        "⚔️ Aether Duel",
        f"**{challenger}** vs **{opponent}**",
        color=color,
    )
    embed.add_field(
        name=f"🔵 {challenger}",
        value=f"{progress_bar(state.challenger_hp, 100)} `{state.challenger_hp}`",
    )
    embed.add_field(
        name=f"🔴 {opponent}",
        value=f"{progress_bar(state.opponent_hp, 100)} `{state.opponent_hp}`",
    )
    if state.log:
        embed.add_field(
            name="📜 Сүүлийн үйлдэл", value="\n".join(state.log), inline=False
        )
    if state.status == "done":
        embed.add_field(
            name="🏆 Ялагч",
            value=f"<@{state.winner_id}> · +{format_number(state.payout)} ⛃",
        )
    else:
        embed.add_field(name="🎯 Ээлж", value=f"<@{state.turn_id}>", inline=False)
    embed.set_footer(text="✦ Aether System • Attack / Skill / Defend")
    return embed


def help_embed() -> discord.Embed:
    return base_embed(
        "✦ AETHER SYSTEM — Тусламж",
        "Доорх цэснээс категори сонгоно уу. Бүх тоглогчийн команд `a!` "
        "prefix-тэй, админ команд зөвхөн `/admin_*` slash хэлбэртэй.",
        color=config.PRIMARY,
    )
