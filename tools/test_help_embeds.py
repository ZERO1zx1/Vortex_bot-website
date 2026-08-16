"""Validate every help.py embed builds without violating Discord limits.

Checks:
- Each embed field name <= 256 chars, value <= 1024 chars
- Full embed (title+description+fields) <= 6000 chars
Runs entirely offline (no Discord traffic, no Supabase connection).
"""
import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DISCORD_TOKEN", "0")
os.environ.setdefault("SUPABASE_URL", "https://fake.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiJ9.0.0")

import discord  # noqa: E402
from discord import ui  # noqa: E402
from unittest.mock import MagicMock

spec = importlib.util.spec_from_file_location("help_cog", "cogs/help.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BUILD_EMBED_OK = 0
BUILD_EMBED_FAIL = 0
DETAIL_EMBED_OK = 0
DETAIL_EMBED_FAIL = 0
FAILURES = []

# ---- 1. Category embeds (build_embed on HelpView) ----
bot = MagicMock()
fake_author = MagicMock()
fake_author.name = "CmdTest"
fake_author.display_avatar.url = "https://example.com/a.png"
fake_author.__str__ = lambda self: "CmdTest"
fake_ctx = MagicMock()
fake_ctx.author = fake_author

for category in mod.CATEGORY_EMOJIS:
    view = mod.HelpView(fake_ctx, list(mod.CATEGORY_EMOJIS.keys()), default_category=category)
    try:
        embed = view.build_embed(category)
        # replicate discord.py embed length validation
        total = len(embed.title or "") + len(embed.description or "")
        for f in embed.fields:
            total += len(f.name or "") + len(f.value or "")
            if len(f.name or "") > 256:
                raise ValueError(f"field name too long: {f.name[:50]}")
            if len(f.value or "") > 1024:
                raise ValueError(f"field value too long in {category}: {len(f.value)} chars")
        if total > 6000:
            raise ValueError(f"embed total too long in {category}: {total}")
        BUILD_EMBED_OK += 1
    except Exception as exc:
        BUILD_EMBED_FAIL += 1
        FAILURES.append(f"build_embed({category}): {exc}")

# ---- 2. Command detail embeds ----
for cmd, info in mod.COMMAND_INFO.items():
    try:
        embed = discord.Embed(
            title=f"{mod.CATEGORY_EMOJIS.get(info['category'], '📁')}  `{cmd}`",
            description=f"**{info['description_mn']}**\n*{info['description_en']}*",
            color=mod.CATEGORY_COLORS.get(info["category"], 0x89B4FA),
        )
        embed.add_field(name="📂 Ангилал", value=f"{mod.CATEGORY_EMOJIS.get(info['category'], '📁')} {info['category']}", inline=True)
        embed.add_field(name="⚙️ Хэрэглэх хэлбэр", value=f"```\n{info['usage']}\n```", inline=True)
        if info.get("examples"):
            embed.add_field(name="📝 Жишээ", value="\n".join(f"`{ex}`" for ex in info["examples"]), inline=False)
        embed.set_author(name="CmdTest", icon_url="https://example.com/a.png")
        embed.set_footer(text=f"{mod.BOT_NAME} · Тусламжийн систем · {mod.BOT_FOOTER}")
        total = len(embed.title or "") + len(embed.description or "")
        for f in embed.fields:
            total += len(f.name or "") + len(f.value or "")
            if len(f.value or "") > 1024:
                raise ValueError(f"value too long for {cmd}: {len(f.value)}")
        if total > 6000:
            raise ValueError(f"total too long for {cmd}: {total}")
        DETAIL_EMBED_OK += 1
    except Exception as exc:
        DETAIL_EMBED_FAIL += 1
        FAILURES.append(f"detail({cmd}): {exc}")

print(f"Category embeds : OK={BUILD_EMBED_OK} FAIL={BUILD_EMBED_FAIL}")
print(f"Detail embeds   : OK={DETAIL_EMBED_OK} FAIL={DETAIL_EMBED_FAIL}")
for f in FAILURES[:20]:
    print("FAIL:", f)
