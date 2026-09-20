"""Centralized branding / bot identity configuration.

Change the bot's public identity here instead of searching through cogs.
"""

from typing import Optional
from datetime import datetime, timezone

BOT_NAME = "𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹"
BOT_DESCRIPTION = (
    "Эдийн засаг, level, дэлгүүр, тоглоом, модерац болон бусад олон "
    "функцтэй Монгол Discord бот."
)
BOT_FOOTER = f"{BOT_NAME} • Монгол Discord бот"
BOT_ICON_URL = None  # Set to a CDN URL if you want a footer icon

# Optional external links
SUPPORT_URL = None
WEBSITE_URL = None
INVITE_URL = None

# Brand color
# Neon anime / cyberpunk palette shared by every embed surface.
PRIMARY_COLOR = 0x090B1A
SUCCESS_COLOR = 0x72F1B8
ERROR_COLOR = 0xFF5C8A
WARNING_COLOR = 0xFFD166
GOLD_COLOR = 0xFFB86B
INFO_COLOR = 0x63D9FF
ACCENT_COLOR = 0xC77DFF
MUTED_COLOR = 0x737B9C


def footer_text(user: Optional[str] = None) -> str:
    """Build a consistent footer string, optionally attributing a user."""
    if user:
        return f"{user} • {BOT_FOOTER}"
    return BOT_FOOTER


def timestamp_now() -> datetime:
    return datetime.now(timezone.utc)
