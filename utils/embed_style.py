from datetime import datetime, timezone
from discord import Embed
from utils.branding import BOT_NAME
from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR

ICONS = {
    "success": "✅",
    "error": "❌",
    "warning": "⚠️",
    "info": "ℹ️",
    "money": "💰",
    "bank": "🏦",
    "work": "💼",
    "daily": "📅",
    "game": "🎮",
    "casino": "🎰",
    "level": "✨",
    "rank": "📈",
    "shop": "🛍️",
    "item": "📦",
    "gift": "🎁",
    "heart": "💖",
    "marriage": "💒",
    "mod": "🛡️",
    "admin": "⚙️",
    "role": "🎭",
    "invite": "📨",
    "voice": "🔊",
    "music": "🎵",
    "food": "🍜",
    "trade": "🔄",
    "market": "🏪",
    "stock": "📊",
    "leaderboard": "🏆",
    "quest": "📜",
    "pet": "🐾",
    "mine": "⛏️",
    "pvp": "⚔️",
    "confess": "🤫",
    "counting": "🔢",
    "lang": "🌐",
    "help": "❓",
    "avatar": "🖼️",
    "profile": "👤",
    "inventory": "🎒",
    "time": "⏰",
    "lock": "🔒",
    "unlock": "🔓",
    "ban": "🔨",
    "kick": "👢",
    "timeout": "🔇",
    "clear": "🧹",
    "warn": "⚠️",
    "prison": "🚔",
    "protect": "🛡️",
    "transfer": "💸",
    "deposit": "📥",
    "withdraw": "📤",
    "rob": "🏃‍♂️",
    "hack": "💻",
    "gamble": "🎲",
    "slot": "🎰",
    "coinflip": "🪙",
    "dice": "🎲",
    "rps": "✊",
    "blackjack": "🃏",
    "roulette": "🎯",
    "highlow": "📈",
}

BOX_TOP = "┏━━━━━━━━━━━━━━━━━━━━━━━━━━┓"
BOX_BOT = "┗━━━━━━━━━━━━━━━━━━━━━━━━━━┛"
BOX_MID = "┃ {label}: {value:<20} ┃"
SEP = "━" * 30


def style_embed(title: str, description: str = "", color: int = EMBED_COLOR, icon_key: str = "") -> Embed:
    icon = ICONS.get(icon_key, "")
    full_title = f"{icon}  {title}  {icon}" if icon else title
    ts = datetime.now(timezone.utc)
    e = Embed(title=full_title, description=description, color=color, timestamp=ts)
    e.set_footer(text=f"{BOT_NAME} • {ts.strftime('%H:%M:%S')}")
    return e


def success_embed(title: str, desc: str = "") -> Embed:
    return style_embed(title, desc, SUCCESS_COLOR, "success")


def error_embed(title: str, desc: str = "") -> Embed:
    return style_embed(title, desc, ERROR_COLOR, "error")


def warning_embed(title: str, desc: str = "") -> Embed:
    return style_embed(title, desc, WARNING_COLOR, "warning")


def info_embed(title: str, desc: str = "") -> Embed:
    return style_embed(title, desc, INFO_COLOR, "info")


def gold_embed(title: str, desc: str = "") -> Embed:
    return style_embed(title, desc, GOLD_COLOR, "gift")


def add_box_field(embed: Embed, name: str, lines: list, inline: bool = False) -> Embed:
    content = "\n".join(lines)
    embed.add_field(name=f"📋  {name}", value=f"```\n{content}\n```", inline=inline)
    return embed


def add_kv_field(embed: Embed, name: str, data: dict, inline: bool = False) -> Embed:
    lines = [f"╭ {k}" + "\n╰→ {v}" for k, v in data.items()]
    content = "\n".join(lines)
    embed.add_field(name=f"📋  {name}", value=content, inline=inline)
    return embed


def format_command(cmd: str, desc: str, usage: str) -> str:
    return f"╭ **`{cmd}`**\n╰→ {desc}\n  ↳ `{usage}`"


def format_list(items: list, icon: str = "▸") -> str:
    return "\n".join(f"{icon} **`{item}`**" for item in items)