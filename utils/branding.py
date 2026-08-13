"""Centralized branding / bot identity configuration.

Change the bot's public identity here instead of searching through cogs.
"""

BOT_NAME = "𝓐𝓮𝓽𝓰𝓮𝓻  蒼穹"
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
PRIMARY_COLOR = 0x1E1E2F
SUCCESS_COLOR = 0xA6E3A1
ERROR_COLOR = 0xF38BA8
WARNING_COLOR = 0xF9E2AF
GOLD_COLOR = 0xFAB387
INFO_COLOR = 0x89B4FA


def footer_text(user: str = None) -> str:
    """Build a consistent footer string, optionally attributing a user."""
    if user:
        return f"{user} • {BOT_FOOTER}"
    return BOT_FOOTER
