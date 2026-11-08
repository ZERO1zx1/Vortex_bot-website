import asyncio
import io
import json
import logging
import os
import random
import time
import weakref
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiohttp
import discord
from discord import ui
from discord.ext import commands, tasks
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from src.utils import journal_style as journal
from src.utils.branding import BOT_NAME
from src.utils.fonts import draw_text_with_fallback
from src.utils.fonts import load_font as _load_font
from src.utils.http_images import download_public_image
from src.utils.supabase_cog import SupabaseCog
from src.core.exceptions import DatabaseUnavailableError
from src.cogs.economy.leaderboard import LeaderboardView

# ── Logger ──
log = logging.getLogger(__name__)

# Зургийн response-ийн хэмжээний дээд хязгаар (5 MiB).
MAX_IMAGE_BYTES = 5 * 1024 * 1024

# ── Asset paths ──
ASSETS_DIR = str(Path(__file__).resolve().parents[2] / "assets")
DEFAULT_ASSET_FONT = os.path.join(ASSETS_DIR, "fonts", "levelfont.otf")
os.makedirs(ASSETS_DIR, exist_ok=True)

# ── Color constants (single source) ──
EMBED_COLOR   = 0x090B1A
SUCCESS_COLOR = 0x72F1B8
GOLD_COLOR    = 0xFFB86B
WARNING_COLOR = 0xFFD166
ERROR_COLOR   = 0xFF5C8A
INFO_COLOR    = 0x63D9FF

# ── Defaults ──
DEFAULT_MESSAGE_XP = 15
DEFAULT_XP_VOICE_TALKING = 4
DEFAULT_MSG_COOLDOWN = 60
DEFAULT_VOICE_XP_PER_MINUTE = 4
DEFAULT_PROG_TYPE = "arithmetic"
DEFAULT_PROG_BASE = 100
DEFAULT_PROG_STEP = 150
VOICE_INTERVAL_SECS = 180

# ── In-memory TTL caches (perf) ──
_CFG_CACHE: dict[int, tuple] = {}      # guild_id -> (expires_at, cfg)
_EXC_CACHE: dict[int, tuple] = {}      # guild_id -> (expires_at, {"channels":[],"users":[]})
_ROLE_XP_CACHE: dict[int, tuple] = {}   # guild_id -> (expires_at, multiplier rows)
_CACHE_TTL = 20.0

# ── Safe converters ──
def _safe_int(value, default=0):
    try: return int(value)
    except (TypeError, ValueError, OverflowError):
        return default

def _safe_float(value, default=0.0):
    try: return float(value)
    except (TypeError, ValueError):
        return default

def _safe_bool(value, default=False):
    if isinstance(value, bool): return value
    if isinstance(value, int): return bool(value)
    if isinstance(value, str): return value.lower() in ('1','true','yes','on')
    return default

def _parse_id_list(raw):
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return []
    if not isinstance(raw, list):
        return []
    return [int(value) for value in raw if str(value).isdigit()]

def _format_template(template, *, member=None, guild=None, channel=None, level=None, xp=None):
    values = {
        "mention": getattr(member, "mention", "") if member else "",
        "name": getattr(member, "display_name", "") if member else "",
        "displayname": getattr(member, "display_name", "") if member else "",
        "username": getattr(member, "name", "") if member else "",
        "guild-name": getattr(guild, "name", "") if guild else "",
        "channel": getattr(channel, "mention", "") if channel else "",
        "channel-name": getattr(channel, "name", "") if channel else "",
        "level": level if level is not None else "",
        "xp": xp if xp is not None else "",
    }
    result = str(template or "")
    for key, value in values.items():
        result = result.replace("{" + key + "}", str(value))
    return result

# ── XP progression math ──
def xp_for_level(level: int, cfg: dict[str, Any]) -> int:
    if cfg.get("prog_type") == "geometric":
        mult = float(cfg.get("prog_step", 1.5))
        return max(1, int(cfg.get("prog_base", 100) * (mult ** level)))
    return max(1, cfg.get("prog_base", 100) + level * int(cfg.get("prog_step", 150)))

def xp_for_message(content: str, cfg: dict[str, Any]) -> int:
    # Engauge defaults to 15 XP, while allowing each server to configure it.
    return max(0, _safe_int(cfg.get("xp_message"), DEFAULT_MESSAGE_XP))

# ── Avatar / image helpers (used by DLC card) ──
async def fetch_avatar(url, size=128):
    if not isinstance(url, str) or not url.strip():
        return Image.new("RGBA", (size, size), (88, 101, 242, 255))
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10),
            trust_env=False,
            auto_decompress=False,
            headers={"Accept-Encoding": "identity"},
        ) as session, session.get(url, allow_redirects=False) as resp:
            # Reject non-identity content encoding
            content_encoding = resp.headers.get("Content-Encoding", "").lower()
            if content_encoding and content_encoding != "identity":
                raise ValueError(f"Content-Encoding '{content_encoding}' not allowed")
            resp.raise_for_status()
            # Response-ийн хэмжээг хязгаарлана.
            data = await resp.content.read(MAX_IMAGE_BYTES + 1)
            if len(data) > MAX_IMAGE_BYTES:
                raise ValueError("image response too large")
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size), resample=Resampling.LANCZOS)
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError, TypeError):
        log.debug("Avatar download failed; using fallback", exc_info=True)
        img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    img.putalpha(mask)
    return img

async def _load_background_image(url: str | None):
    if not url:
        return None
    try:
        data = await download_public_image(url)
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 16_000_000:
                raise ValueError("Background image exceeds the pixel limit")
            return image.convert("RGBA")
    except (aiohttp.ClientError, TimeoutError, OSError, ValueError, Image.DecompressionBombError):
        log.warning("Background image unavailable; using the default card", exc_info=True)
    return None

async def _load_overlay(overlay_name: str, width: int, height: int):
    if not overlay_name:
        return None
    candidates = [
        os.path.join(ASSETS_DIR, overlay_name),
        os.path.join(os.path.dirname(__file__), "assets", overlay_name),
        os.path.join(os.getcwd(), "assets", overlay_name),
    ]
    for path in candidates:
        if path and os.path.exists(path):
            try:
                overlay = Image.open(path).convert("RGBA")
                return overlay.resize((width, height), resample=Resampling.LANCZOS)
            except (OSError, ValueError):
                log.exception("Operation failed in _load_overlay")
    return None

def _load_asset_font(size: int, bold: bool = True):
    try:
        return _load_font(size, bold)
    except (OSError, ValueError):
        log.exception("Operation failed in _load_asset_font")
        return ImageFont.load_default()

# ── Config load/save (with TTL cache) ──
async def get_config(db_manager, guild_id: int) -> dict[str, Any]:
    gid = int(guild_id)
    now = time.monotonic()
    hit = _CFG_CACHE.get(gid)
    if hit and hit[0] > now:
        return hit[1]
    stale_cfg = hit[1] if hit else None
    try:
        row = await db_manager.fetchone("leveling_config", {"guild_id": str(guild_id)})
    except DatabaseUnavailableError as e:
        log.warning("Leveling config temporarily unavailable for guild %s: %s", guild_id, e)
        # A transient Supabase outage must not replace a known-good config with
        # defaults (which could silently enable/disable XP or crates).
        if stale_cfg is not None:
            return stale_cfg
        row = None
    except Exception as e:
        log.exception("Operation failed in get_config")
        if all(code not in str(e) for code in ("PGRST202", "PGRST205")) and getattr(e, "status_code", None) != 404:
            raise
        row = None
    if not row:
        cfg = {
            "enabled": True, "announce_channel": None, "voice_xp_enabled": True,
            "level_message": "{mention} Level {level} хүрлээ!",
            "xp_message": DEFAULT_MESSAGE_XP,
            "prog_type": "arithmetic", "prog_base": 100, "prog_step": 150,
            "xp_voice_talking": DEFAULT_VOICE_XP_PER_MINUTE, "msg_cooldown": 60,
            "background_url": None, "xp_drop_enabled": False,
            "xp_drop_channel": None, "xp_drop_min": 100, "xp_drop_max": 500,
            "xp_drop_interval": 3600, "xp_drop_redeem_seconds": 300,
            "xp_drop_cooldown": 60, "xp_drop_max_redeemers": 0,
            "xp_drop_criteria": "time", "xp_drop_message_count": 100,
            "xp_drop_contributing_channels": [],
        }
    else:
        cols = ["guild_id","enabled","announce_channel","voice_xp_enabled","level_message","xp_message","prog_type","prog_base","prog_step","xp_voice_talking","msg_cooldown","background_url","xp_drop_enabled","xp_drop_channel","xp_drop_min","xp_drop_max","xp_drop_interval","xp_drop_redeem_seconds","xp_drop_cooldown","xp_drop_max_redeemers","xp_drop_criteria","xp_drop_message_count","xp_drop_contributing_channels","xp_drop_message"]
        data = {key: row.get(key) for key in cols}
        cfg = {
            "enabled": _safe_bool(data.get("enabled"), True),
            "announce_channel": data.get("announce_channel"),
            "voice_xp_enabled": _safe_bool(data.get("voice_xp_enabled"), True),
            "level_message": data.get("level_message") or "{mention} Level {level} хүрлээ!",
            "xp_message": _safe_int(data.get("xp_message"), DEFAULT_MESSAGE_XP),
            "prog_type": data.get("prog_type") or "arithmetic",
            "prog_base": _safe_int(data.get("prog_base"), 100),
            "prog_step": _safe_float(data.get("prog_step"), 150.0),
            "xp_voice_talking": _safe_int(data.get("xp_voice_talking"), DEFAULT_VOICE_XP_PER_MINUTE),
            "msg_cooldown": _safe_int(data.get("msg_cooldown"), 60),
            "background_url": data.get("background_url"),
            "xp_drop_enabled": _safe_bool(data.get("xp_drop_enabled"), False),
            "xp_drop_channel": data.get("xp_drop_channel"),
            "xp_drop_min": _safe_int(data.get("xp_drop_min"), 100),
            "xp_drop_max": _safe_int(data.get("xp_drop_max"), 500),
            "xp_drop_interval": _safe_int(data.get("xp_drop_interval"), 3600),
            "xp_drop_redeem_seconds": _safe_int(data.get("xp_drop_redeem_seconds"), 300),
            "xp_drop_cooldown": _safe_int(data.get("xp_drop_cooldown"), 60),
            "xp_drop_max_redeemers": _safe_int(data.get("xp_drop_max_redeemers"), 0),
            "xp_drop_criteria": data.get("xp_drop_criteria") or "time",
            "xp_drop_message_count": _safe_int(data.get("xp_drop_message_count"), 100),
            "xp_drop_contributing_channels": _parse_id_list(data.get("xp_drop_contributing_channels")),
            "xp_drop_message": data.get("xp_drop_message") or "🌟 {xp} XP crate drop боллоо!",
        }
    _CFG_CACHE[gid] = (now + _CACHE_TTL, cfg)
    return cfg

async def set_config(db_manager, guild_id: int, cfg: dict[str, Any]):
    data = {
        "guild_id": str(guild_id),
        "enabled": bool(cfg.get("enabled", True)),
        "announce_channel": cfg.get("announce_channel"),
        "voice_xp_enabled": bool(cfg.get("voice_xp_enabled", True)),
        "level_message": cfg.get("level_message", "{mention} Level {level} хүрлээ!"),
        "xp_message": max(0, int(cfg.get("xp_message", DEFAULT_MESSAGE_XP))),
        "prog_type": cfg.get("prog_type", "arithmetic"),
        "prog_base": int(cfg.get("prog_base", 100)),
        "prog_step": float(cfg.get("prog_step", 150)),
        "xp_voice_talking": int(cfg.get("xp_voice_talking", DEFAULT_VOICE_XP_PER_MINUTE)),
        "msg_cooldown": int(cfg.get("msg_cooldown", 60)),
        "background_url": cfg.get("background_url"),
        "xp_drop_enabled": bool(cfg.get("xp_drop_enabled", False)),
        "xp_drop_channel": cfg.get("xp_drop_channel"),
        "xp_drop_min": int(cfg.get("xp_drop_min", 100)),
        "xp_drop_max": int(cfg.get("xp_drop_max", 500)),
        "xp_drop_interval": int(cfg.get("xp_drop_interval", 3600)),
        "xp_drop_redeem_seconds": int(cfg.get("xp_drop_redeem_seconds", 300)),
        "xp_drop_cooldown": int(cfg.get("xp_drop_cooldown", 60)),
        "xp_drop_max_redeemers": int(cfg.get("xp_drop_max_redeemers", 0)),
        "xp_drop_criteria": cfg.get("xp_drop_criteria", "time"),
        "xp_drop_message_count": int(cfg.get("xp_drop_message_count", 100)),
        "xp_drop_contributing_channels": json.dumps(cfg.get("xp_drop_contributing_channels", [])),
        "xp_drop_message": cfg.get("xp_drop_message", "🌟 {xp} XP crate drop боллоо!"),
    }
    await db_manager.execute("leveling_config", data)
    _CFG_CACHE.pop(int(guild_id), None)

# ── Rank card renderer: "Inked Path" journal page ──
async def render_dlc_card(member, level, current_xp, needed_xp, rank_pos, background_url=None, stamp_text=None):
    try:
        width, height = 900, 380
        seed = abs(hash(getattr(member, "id", 7))) % 997
        base = journal.parchment((width, height), seed=seed)

        if background_url:
            try:
                background = await _load_background_image(background_url)
                if background:
                    background = background.resize((width, height), resample=Resampling.LANCZOS)
                    base = Image.blend(background.convert("RGBA"), base, 0.6)
            except (OSError, ValueError, TypeError) as e:
                log.debug("rank card background skipped: %s", e, exc_info=True)

        draw = ImageDraw.Draw(base)

        avatar_url = None
        try:
            avatar_url = getattr(member.display_avatar, "url", None)
            if avatar_url and hasattr(member.display_avatar, "replace"):
                avatar_url = member.display_avatar.replace(size=256, format="png").url
        except AttributeError as e:
            log.debug("rank card avatar URL failed: %s", e)
            avatar_url = None

        avatar = None
        if avatar_url:
            avatar = await fetch_avatar(avatar_url, 160)
        if avatar is None:
            avatar = Image.new("RGBA", (160, 160), (88, 101, 242, 255))

        avatar = avatar.convert("RGBA").resize((160, 160), resample=Resampling.LANCZOS)
        journal.sketch_frame(base, (64, 120, 224, 280), avatar, seed=seed)
        journal.ink_border(draw, (width, height), seed=seed)

        font_main = _load_asset_font(44, bold=True)
        font_sub = _load_asset_font(26, bold=False)
        font_small = _load_asset_font(17, bold=False)
        font_seal = _load_asset_font(24, bold=True)

        journal.banner(draw, (268, 36, 650, 84), member.display_name[:24], font_main, seed=seed)
        draw_text_with_fallback(draw, (272, 92), "ANIME RANK RECORD", font_small,
                                fill=journal.INK_SOFT, size=17, bold=True)
        journal.wax_seal(draw, (772, 92), 58, f"LVL {level}", font_seal, seed=seed)

        journal.patch(draw, (636, 168, 856, 204))
        rank_txt = f"Rank #{rank_pos}"
        try:
            rtw = draw.textlength(rank_txt, font=font_sub)
        except AttributeError:
            rtw = draw.textsize(rank_txt, font=font_sub)[0]
        draw.text(((636 + 856 - rtw) / 2, 172), rank_txt, font=font_sub, fill=journal.INK)

        progress = current_xp / max(1, needed_xp)
        journal.watercolor_bar(draw, (268, 232, 800, 264), progress,
                               journal.LEAF, journal.RIVER, seed=seed)
        xp_text = f"{current_xp:,}/{needed_xp:,} XP"
        try:
            tx_w = draw.textlength(xp_text, font=font_small)
        except AttributeError:
            tx_w = draw.textsize(xp_text, font=font_small)[0]
        draw.text((268 + (532 - tx_w) / 2, 238), xp_text, font=font_small, fill=journal.CHALK)

        footer_text = f"{member.name} • {BOT_NAME}-ийн аялагчийн тэмдэглэл"
        draw_text_with_fallback(draw, (268, 300), footer_text, font_small, fill=journal.INK_SOFT, size=17, bold=False)

        if stamp_text:
            journal.stamp_burst(base, draw, (140, 62), 50, stamp_text, font_sub, seed=seed)

        buffer = io.BytesIO()
        base.save(buffer, "PNG")
        buffer.seek(0)
        return buffer
    except Exception:
        log.exception("Rank card render failed")
        return None

# ── UI Views (shared by level_admin cog) ──
class XPDropView(ui.View):
    def __init__(self, xp_amount, cog, redeem_seconds=300, max_redeemers=0):
        super().__init__(timeout=max(30, int(redeem_seconds)))
        self.xp_amount = xp_amount; self.cog = cog; self.claimed = set()
        self.max_redeemers = max(0, int(max_redeemers))
    @ui.button(label="🎉 XP авах", style=discord.ButtonStyle.success)
    async def claim(self, interaction, button):
        if interaction.user.id in self.claimed:
            return await interaction.response.send_message("❌ Та аль хэдийн авсан.", ephemeral=True)
        if self.max_redeemers and len(self.claimed) >= self.max_redeemers:
            return await interaction.response.send_message("❌ Энэ XP drop-ийн бүх шагнал авсан байна.", ephemeral=True)
        self.claimed.add(interaction.user.id)
        try:
            await self.cog.add_xp(interaction.user.id, interaction.guild.id, self.xp_amount,
                                  member=interaction.guild.get_member(interaction.user.id))
        except Exception:
            # A transient database/Discord failure must not permanently burn
            # the member's claim. Put it back so the same drop can be retried.
            self.claimed.discard(interaction.user.id)
            log.exception("XP drop claim failed for user %s", interaction.user.id)
            return await interaction.response.send_message(
                "⚠️ XP олгоход түр алдаа гарлаа. Дахин оролдоно уу.", ephemeral=True
            )
        await interaction.response.send_message(f"✅ +{self.xp_amount} XP авлаа!", ephemeral=True)


def is_audible_voice_member(member, channel) -> bool:
    """Match Engauge voice eligibility: 2+ human members, not muted/deafened."""
    voice = getattr(member, "voice", None)
    if voice is None or getattr(voice, "channel", None) is None:
        return False
    humans = [m for m in getattr(channel, "members", ()) if not getattr(m, "bot", False)]
    if len(humans) < 2:
        return False
    return not any((getattr(voice, key, False) for key in ("mute", "self_mute", "deaf", "self_deaf")))

# ================== MAIN COG ==================
class Leveling(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None
        self._msg_cooldown = {}
        self._voice_join = {}
        self._voice_last_xp = {}
        self.voice_task = None
        self.xp_drop_task = None
        # guild_id -> epoch seconds of the last XP drop actually posted.
        self._xp_drop_last = {}
        self._xp_drop_message_counts = {}
        # Serializes every read-modify-write on the `levels` row for a given
        # (user, guild). XP/level and message_count live in the SAME row, so
        # they must share one lock or a concurrent _add_xp upsert would clobber
        # an in-flight message_count update (and vice versa).
        #
        # Weak keys on values: a lock only needs to outlive the critical
        # section that holds it, so an idle member's lock is reclaimed instead
        # of the pool growing for every pair ever seen. Same pattern as
        # `level_admin._CONFIG_LOCKS`.
        self._xp_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def _user_xp_lock(self, user_id, guild_id) -> asyncio.Lock:
        key = f"{user_id}:{guild_id}"
        lock = self._xp_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._xp_locks[key] = lock
        return lock

    async def cog_load(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        self.voice_task = asyncio.create_task(self._voice_xp_loop())
        self.xp_drop_task = self.xp_drop_loop.start()

    async def cog_unload(self):
        if self.voice_task: self.voice_task.cancel()
        if self.xp_drop_task: self.xp_drop_task.cancel()
        if self.session: await self.session.close()

    async def init_db(self):
        pass

    def _on_cooldown(self, storage, user_id, seconds, guild_id=0):
        now = time.monotonic()
        key = (guild_id, user_id)
        last = storage.get(key, 0)
        if now - last < seconds: return True
        storage[key] = now
        return False

    async def _add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        if amount == 0: return
        if member and check_mute:
            try:
                if member.timed_out_until and member.timed_out_until > datetime.now(UTC): return
                if hasattr(member,'voice') and member.voice and (member.voice.mute or member.voice.self_mute): return
            except Exception:
                log.exception("Operation failed in _add_xp")
        if amount > 0 and member is not None:
            try:
                now = time.monotonic()
                cached = _ROLE_XP_CACHE.get(int(guild_id))
                if cached and cached[0] > now:
                    role_rows = cached[1]
                else:
                    role_rows = await self.bot.db_manager.fetch_all(
                        "level_role_xp_multipliers", {"guild_id": str(guild_id)}
                    )
                    _ROLE_XP_CACHE[int(guild_id)] = (now + _CACHE_TTL, role_rows)
                member_role_ids = {getattr(role, "id", None) for role in getattr(member, "roles", ())}
                matched = [
                    row for row in role_rows
                    if int(row.get("role_id", 0) or 0) in member_role_ids
                ]
                if any(float(row.get("multiplier", 1) or 1) == 0 for row in matched):
                    amount = 0
                elif matched:
                    role_by_id = {getattr(role, "id", None): role for role in getattr(member, "roles", ())}
                    selected = max(
                        matched,
                        key=lambda row: getattr(role_by_id.get(int(row["role_id"])), "position", 0),
                    )
                    amount = int(amount * max(0, float(selected.get("multiplier", 1) or 1)))
            except Exception:
                log.exception("Operation failed applying role XP multiplier")
        # The read-modify-write below must be atomic per user: XP is granted
        # from on_message, the voice loop, and explicit crates, any of which
        # can interleave. Without the lock two grants both read xp=N and both
        # write N+15, silently destroying the other grant (and skipping the
        # level-up that the lost XP should have triggered).
        async with self._user_xp_lock(user_id, guild_id):
            row = await self.bot.db_manager.fetch_one(
                "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
            )
            xp, level = (row.get("xp", 0) or 0, row.get("level", 1) or 1) if row else (0, 1)
            old_level = level
            new_xp = xp + amount
            cfg = await get_config(self.bot.db_manager, guild_id)
            leveled_up = False
            reached_levels = []
            while new_xp < 0 and level > 1:
                level -= 1
                new_xp += xp_for_level(level, cfg)
            new_xp = max(new_xp, 0)
            while True:
                needed = xp_for_level(level, cfg)
                if new_xp >= needed:
                    new_xp -= needed; level += 1; leveled_up = True
                    reached_levels.append(level)
                else: break
            await self.bot.db_manager.upsert(
                "levels",
                {"user_id": str(user_id), "guild_id": str(guild_id), "xp": new_xp, "level": level},
                on_conflict="user_id,guild_id",
            )
        if leveled_up and member:
            await self._announce_level_up(member, old_level, level, new_xp, channel, reached_levels)
            try:
                quests = self.bot.get_cog("Quests")
                if quests and hasattr(quests,'trigger_event'): await quests.trigger_event(member.id, guild_id, "level_up", 1)
            except Exception:
                log.exception("Operation failed in _add_xp")

    async def _grant_level_reward(self, member, guild, reached, amount):
        """Credit a level-up reward exactly once.

        update_balance is reference-based, so retrying cannot double-pay.
        The credit used to sit inside the level-up handler's broad
        ``except Exception``, which swallowed the failure and left the member
        silently without the reward.
        """
        economy = self.bot.get_cog("Economy")
        if not economy:
            return None
        reference = f"level_reward:{guild.id}:{member.id}:{reached}"
        last_error = None
        for attempt in range(3):
            try:
                return await economy.update_balance(
                    member.id, guild.id, amount, reference=reference,
                )
            except Exception as exc:
                last_error = exc
                # log.exception ашиглана: repo-ийн бусад хэсэгтэй нэг хэвэр
                # (ruff BLE001 нь log.exception-тэй handler-ийг зөвшөөрнө).
                log.exception(
                    "level reward attempt %s failed (reference=%s)",
                    attempt + 1, reference,
                )
                await asyncio.sleep(0.5 * (attempt + 1))
        log.error(
            "level reward permanently failed reference=%s user=%s guild=%s: %s",
            reference, member.id, guild.id, last_error,
        )
        return None

    async def _announce_level_up(self, member, old, new, current_xp, source_channel, reached_levels=None):
        guild = member.guild
        cfg = await get_config(self.bot.db_manager, guild.id)
        reached_levels = reached_levels or [new]
        role_level_message = None
        for reached in reached_levels:
            try:
                reward_row = await self.bot.db_manager.fetch_one(
                    "level_rewards", {"guild_id": str(guild.id), "level": reached}
                )
                if reward_row and (reward_row.get("money", 0) or 0) > 0:
                    granted = await self._grant_level_reward(member, guild, reached, reward_row["money"])
                    if granted is None:
                        # Шагнал очихгүй болсон бол "авлаа" гэсэн зары
                        # гаргахгүй — тэгэхгүй бол хэрэглэгчид худал мэдээлэл
                        # үзнэ. reference-ийг log-оос шууд replay болгож болно.
                        continue
                    embed = discord.Embed(title="🎁 Түвшний шагнал!", description=f"{member.mention} Lv.{reached} хүрсэн тул **{reward_row['money']:,}₮** авлаа!", color=GOLD_COLOR)
                    ch = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
                    if ch:
                        try: await ch.send(embed=embed)
                        except discord.HTTPException:
                            log.exception("Operation failed in _announce_level_up")
            except Exception:
                log.exception("Level reward failed")
            try:
                role_row = await self.bot.db_manager.fetch_one(
                    "level_roles", {"guild_id": str(guild.id), "level": reached}
                )
                if role_row:
                    if role_row.get("level_message"):
                        role_level_message = role_row["level_message"]
                    try:
                        role = guild.get_role(int(role_row.get("role_id")))
                    except (TypeError, ValueError):
                        role = None
                    if role and role not in member.roles: await member.add_roles(role, reason=f"Level {reached}")
            except Exception as e:
                log.warning("level role grant skipped: %s", e, exc_info=True)
        try:
            await self.sync_level_roles(member)
        except Exception:
            log.exception("Level role stacking sync failed")
        channel = guild.get_channel(cfg.get("announce_channel")) if cfg.get("announce_channel") else source_channel
        if not channel: return
        needed = xp_for_level(new, cfg)
        rank_pos = await self.get_rank_position(member.id, guild.id)
        try:
            buf = await render_dlc_card(member, new, current_xp, needed, rank_pos, cfg.get("background_url"), stamp_text="ASCEND!")
            if buf:
                file = discord.File(buf, filename="levelup.png")
                try:
                    message = _format_template(
                        role_level_message or cfg.get("level_message", "{mention} Level {level} хүрлээ!"),
                        member=member, guild=guild, channel=channel, level=new,
                    )
                    await channel.send(content=message, file=file)
                except discord.HTTPException:
                    log.exception("Operation failed in _announce_level_up")
            else:
                embed = discord.Embed(
                    title="🎉 Түвшин ахисан!",
                    description=_format_template(
                        role_level_message or cfg.get("level_message", "{mention} Level {level} хүрлээ!"),
                        member=member, guild=guild, channel=channel, level=new,
                    ),
                    color=GOLD_COLOR,
                )
                try: await channel.send(embed=embed)
                except discord.HTTPException:
                    log.exception("Operation failed in _announce_level_up")
        except Exception:
            log.exception("Level up announcement failed")

    # ========== PUBLIC API ==========
    async def add_xp(self, user_id, guild_id, amount, member=None, check_mute=True, channel=None):
        await self._add_xp(user_id, guild_id, amount, member, check_mute, channel)
    async def get_total_xp(self, user_id, guild_id):
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        if not row: return 0
        xp = row.get("xp", 0) or 0
        level = row.get("level", 1) or 1
        cfg = await get_config(self.bot.db_manager, guild_id)
        return sum(xp_for_level(l,cfg) for l in range(level)) + xp
    async def get_level(self, user_id, guild_id):
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        return row.get("level", 1) if row else 1
    async def get_rank_position(self, user_id, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="level", desc=True,
        )
        rows.sort(key=lambda r: (r.get("level", 0) or 0, r.get("xp", 0) or 0), reverse=True)
        for i, r in enumerate(rows):
            if int(r.get("user_id")) == int(user_id): return i+1
        return len(rows)+1
    async def get_config(self, guild_id):
        return await get_config(self.bot.db_manager, guild_id)
    def xp_for_level(self, level, cfg):
        return xp_for_level(level, cfg)
    def get_rank_info(self, level):
        if level < 10: return "Эхлэгч", "🌱"
        if level < 25: return "Сонирхогч", "⭐"
        if level < 50: return "Мэргэжилтэн", "🌟"
        if level < 100: return "Мастер", "💎"
        return "Домог", "👑"

    async def get_exceptions(self, guild_id):
        gid = int(guild_id)
        now = time.monotonic()
        hit = _EXC_CACHE.get(gid)
        if hit and hit[0] > now:
            return hit[1]
        try:
            rows = await self.bot.db_manager.fetch_all(
                "leveling_exceptions", {"guild_id": str(guild_id)}
            )
        except DatabaseUnavailableError as e:
            log.warning("Leveling exceptions temporarily unavailable for guild %s: %s", guild_id, e)
            return hit[1] if hit else {"channels": [], "users": []}
        ex = {"channels":[r["target_id"] for r in rows if r.get("type")=="channel"],
              "users":[r["target_id"] for r in rows if r.get("type")=="user"]}
        _EXC_CACHE[gid] = (now + _CACHE_TTL, ex)
        return ex
    async def add_exception(self, guild_id, exc_type, target_id):
        await self.bot.db_manager.upsert(
            "leveling_exceptions",
            {"guild_id": str(guild_id), "type": exc_type, "target_id": target_id},
            on_conflict="guild_id,type,target_id",
        )
        _EXC_CACHE.pop(int(guild_id), None)
    async def remove_exception(self, guild_id, exc_type, target_id):
        await self.bot.db_manager.delete(
            "leveling_exceptions",
            {"guild_id": str(guild_id), "type": exc_type, "target_id": target_id},
        )
        _EXC_CACHE.pop(int(guild_id), None)

    async def get_level_roles(self, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "level_roles", {"guild_id": str(guild_id)}, order_by="level"
        )
        return [{
            "level": r["level"], "role_id": r["role_id"],
            "stacking": r.get("stacking", True) is not False,
            "stacking_group": r.get("stacking_group"),
            "required_role_ids": _parse_id_list(r.get("required_role_ids")),
            "level_message": r.get("level_message"),
        } for r in rows]
    async def set_level_role(self, guild_id, level, role_id):
        await self.bot.db_manager.upsert(
            "level_roles",
            {"guild_id": str(guild_id), "level": level, "role_id": role_id},
            on_conflict="guild_id,level",
        )

    async def set_role_xp_multiplier(self, guild_id, role_id, multiplier):
        await self.bot.db_manager.upsert(
            "level_role_xp_multipliers",
            {"guild_id": str(guild_id), "role_id": role_id, "multiplier": float(multiplier)},
            on_conflict="guild_id,role_id",
        )
        _ROLE_XP_CACHE.pop(int(guild_id), None)

    async def set_level_role_options(self, guild_id, level, stacking, stacking_group=None, required_role_ids=None, level_message=None):
        await self.bot.db_manager.update(
            "level_roles",
            {"guild_id": str(guild_id), "level": level},
            {
                "stacking": bool(stacking), "stacking_group": stacking_group or None,
                "required_role_ids": json.dumps(required_role_ids or []),
                "level_message": level_message or None,
            },
        )
    async def delete_level_role(self, guild_id, level):
        await self.bot.db_manager.delete(
            "level_roles",
            {"guild_id": str(guild_id), "level": level}
        )

    async def sync_level_roles(self, member):
        """Repair all level roles the member should currently have."""
        level = await self.get_level(member.id, member.guild.id)
        rows = await self.get_level_roles(member.guild.id)
        bot_member = member.guild.me
        if bot_member is None or not bot_member.guild_permissions.manage_roles:
            return 0
        eligible = [row for row in rows if int(row["level"]) <= int(level)]
        winners = {}
        for row in eligible:
            if row.get("stacking", True):
                continue
            group = row.get("stacking_group") or "__default__"
            current = winners.get(group)
            if current is None or int(row["level"]) > int(current["level"]):
                winners[group] = row
        granted = 0
        for row in rows:
            role = member.guild.get_role(int(row["role_id"]))
            if role is None or role.is_default() or role.managed or role >= bot_member.top_role:
                continue
            keep = int(row["level"]) <= int(level)
            required = set(row.get("required_role_ids", []))
            if required and not required.issubset({getattr(role, "id", None) for role in member.roles}):
                keep = False
            if keep and not row.get("stacking", True):
                group = row.get("stacking_group") or "__default__"
                keep = winners.get(group) is row
            if keep and role not in member.roles:
                await member.add_roles(role, reason="Level role repair")
                granted += 1
            elif not keep and role in member.roles and not row.get("stacking", True):
                await member.remove_roles(role, reason="Level role stacking")
        return granted

    async def get_level_rewards(self, guild_id):
        rows = await self.bot.db_manager.fetch_all(
            "level_rewards", {"guild_id": str(guild_id)}, order_by="level"
        )
        return [{"level": r["level"], "money": r["money"]} for r in rows]
    async def set_level_reward(self, guild_id, level, money):
        await self.bot.db_manager.upsert(
            "level_rewards",
            {"guild_id": str(guild_id), "level": level, "money": money},
            on_conflict="guild_id,level",
        )
    async def delete_level_reward(self, guild_id, level):
        await self.bot.db_manager.delete(
            "level_rewards",
            {"guild_id": str(guild_id), "level": level}
        )

    # ========== EVENT LISTENERS ==========
    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot: return
        cfg = await get_config(self.bot.db_manager, message.guild.id)
        if not cfg["enabled"]: return
        exc = await self.get_exceptions(message.guild.id)
        if message.channel.id in exc["channels"] or message.author.id in exc["users"]: return
        # Engauge's message counter tracks every eligible message, even when
        # the one-minute XP reward cooldown suppresses the XP grant.
        await self._bump_message_count(message.author.id, message.guild.id)
        if self._on_cooldown(self._msg_cooldown, message.author.id, cfg["msg_cooldown"], message.guild.id): return
        # Engauge rewards a message once per cooldown regardless of its word
        # count or whether it contains an attachment.
        xp = xp_for_message(message.content, cfg)
        try:
            await self._add_xp(
                message.author.id, message.guild.id, xp,
                member=message.author, channel=message.channel,
            )
        except DatabaseUnavailableError as e:
            # A transient Supabase outage must not surface as an unhandled
            # Discord listener error; the next eligible message can retry.
            log.warning("Message XP temporarily skipped for guild %s: %s", message.guild.id, e)
            return
        if cfg.get("xp_drop_enabled") and cfg.get("xp_drop_criteria") == "message_count":
            channels = cfg.get("xp_drop_contributing_channels", [])
            if not channels or message.channel.id in channels:
                guild_id = message.guild.id
                count = self._xp_drop_message_counts.get(guild_id, 0) + 1
                threshold = max(1, int(cfg.get("xp_drop_message_count", 100)))
                if count >= threshold:
                    channel = message.guild.get_channel(cfg.get("xp_drop_channel")) or message.channel
                    if await self._post_xp_drop(message.guild, channel, cfg):
                        self._xp_drop_message_counts[guild_id] = 0
                    else:
                        self._xp_drop_message_counts[guild_id] = count
                else:
                    self._xp_drop_message_counts[guild_id] = count

    async def _bump_message_count(self, user_id, guild_id):
        """Increment `message_count` on the same locked `levels` row.

        The previous version read the row, then retried the write up to three
        times while re-using that same stale value, so a retried write could
        double-count and a concurrent message could lose its increment. The
        lock is shared with `_add_xp` because both mutate the same row.
        """
        try:
            async with self._user_xp_lock(user_id, guild_id):
                row = await self.bot.db_manager.fetch_one(
                    "levels", {"user_id": str(user_id), "guild_id": str(guild_id)}
                )
                current = (row.get("message_count", 0) or 0) if row else 0
                if row:
                    await self.bot.db_manager.update(
                        "levels",
                        {"user_id": str(user_id), "guild_id": str(guild_id)},
                        {"message_count": current + 1},
                    )
                else:
                    await self.bot.db_manager.insert("levels", {
                        "user_id": str(user_id), "guild_id": str(guild_id), "message_count": 1,
                    })
        except Exception:
            log.exception("Operation failed in _bump_message_count")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel and not after.channel:
            key = (member.guild.id, member.id)
            self._voice_join.pop(key, None); self._voice_last_xp.pop(key, None)

    async def _voice_xp_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = time.monotonic()
                for guild in self.bot.guilds:
                    try:
                        cfg = await get_config(self.bot.db_manager, guild.id)
                    except Exception as e:
                        # Нэг guild-ийн DB алдаа (504/timeout г.м.) бусад guild-ыг
                        # зогсоохгүйгээр тухайн guild-г алгасаж үргэлжлүүлнэ.
                        log.warning(f"Voice XP: guild {guild.id} config уншигдсангүй: {e}", exc_info=True)
                        continue
                    if not cfg["enabled"] or not cfg.get("voice_xp_enabled",True): continue
                    exc = await self.get_exceptions(guild.id)
                    for vc in guild.voice_channels:
                        for member in vc.members:
                            if member.bot or member.id in exc["users"]: continue
                            voice = member.voice
                            if not is_audible_voice_member(member, vc): continue
                            key = (guild.id, member.id)
                            if key not in self._voice_join: self._voice_join[key] = now; self._voice_last_xp[key] = now
                            if now - self._voice_last_xp.get(key,0) >= VOICE_INTERVAL_SECS:
                                xp = max(0, int(cfg.get("xp_voice_talking", DEFAULT_VOICE_XP_PER_MINUTE)))
                                self._voice_last_xp[key] = now
                                await self._add_xp(member.id, guild.id, xp, member=member, check_mute=False)
                                try:
                                    lvl_row = await self.bot.db_manager.fetch_one(
                                        "levels", {"user_id": str(member.id), "guild_id": str(guild.id)}
                                    )
                                    if lvl_row:
                                        await self.bot.db_manager.update(
                                            "levels",
                                            {"user_id": str(member.id), "guild_id": str(guild.id)},
                                            {"voice_seconds": (lvl_row.get("voice_seconds", 0) or 0) + VOICE_INTERVAL_SECS},
                                        )
                                    else:
                                        await self.bot.db_manager.insert("levels", {
                                            "user_id": str(member.id), "guild_id": str(guild.id), "voice_seconds": VOICE_INTERVAL_SECS,
                                        })
                                except Exception:
                                    log.exception("Operation failed in _voice_xp_loop")
            except Exception:
                log.exception("Voice XP loop failed")
            await asyncio.sleep(30)

    async def _post_xp_drop(self, guild, channel, cfg):
        minimum = max(1, int(cfg.get("xp_drop_min", 100)))
        maximum = max(minimum, int(cfg.get("xp_drop_max", 500)))
        xp = random.randint(minimum, maximum)
        redeem_seconds = max(30, int(cfg.get("xp_drop_redeem_seconds", 300)))
        cooldown = max(0, int(cfg.get("xp_drop_cooldown", 60)))
        embed = discord.Embed(
            title="🌟 Mystery Crate",
            description=_format_template(
                cfg.get("xp_drop_message", "🌟 {xp} XP crate drop боллоо!"),
                guild=guild, channel=channel, xp=xp,
            ) + f" {redeem_seconds // 60} минутын дотор claim хийнэ үү.",
            color=GOLD_COLOR,
        )
        view = XPDropView(
            xp, self, redeem_seconds=redeem_seconds,
            max_redeemers=int(cfg.get("xp_drop_max_redeemers", 0)),
        )
        await channel.send(embed=embed, view=view)
        self._xp_drop_last[guild.id] = time.time() + redeem_seconds + cooldown
        return True

    @commands.hybrid_command(name="xpdrop", description="Engauge-style XP crate үүсгэх")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_guild=True)
    async def xpdrop(self, ctx):
        cfg = await get_config(self.bot.db_manager, ctx.guild.id)
        if not cfg.get("xp_drop_enabled"):
            return await ctx.send("❌ XP crate систем асаалттай биш байна.", ephemeral=True)
        channel = ctx.guild.get_channel(cfg.get("xp_drop_channel")) or ctx.channel
        try:
            await self._post_xp_drop(ctx.guild, channel, cfg)
        except Exception:
            log.exception("Manual XP crate failed")
            return await ctx.send("❌ XP crate үүсгэж чадсангүй.", ephemeral=True)
        await ctx.send(f"✅ XP crate {channel.mention} сувагт үүслээ.", ephemeral=True)

    @tasks.loop(minutes=1)
    async def xp_drop_loop(self):
        now = time.time()
        for guild in self.bot.guilds:
            try:
                cfg = await get_config(self.bot.db_manager, guild.id)
                if not cfg["xp_drop_enabled"]: continue
                if cfg.get("xp_drop_criteria", "time") != "time": continue
                channel = guild.get_channel(cfg["xp_drop_channel"])
                if not channel: continue
                # `xp_drop_interval` is the configured gap between drops. Once
                # the gap has elapsed, post one drop immediately; adding a
                # second random chance here made a one-hour interval produce
                # drops only about once every ten hours on average.
                interval = max(60, int(cfg["xp_drop_interval"]))
                if now - self._xp_drop_last.get(guild.id, 0) < interval: continue
                await self._post_xp_drop(guild, channel, cfg)
            except Exception:
                log.exception("XP drop failed")

    @xp_drop_loop.before_loop
    async def before_xp_drop_loop(self): await self.bot.wait_until_ready()

    # ========== USER COMMANDS (hybrid) ==========
    @commands.hybrid_command(name="rank", description="Хэрэглэгчийн түвшин, XP болон эрэмбийг харах")
    async def rank(self, ctx, user: discord.Member | None = None):
        target = user or ctx.author
        if ctx.interaction:
            await ctx.defer()
        total_xp = await self.get_total_xp(target.id, ctx.guild.id)
        level = await self.get_level(target.id, ctx.guild.id)
        cfg = await get_config(self.bot.db_manager, ctx.guild.id)
        xp_in_level = total_xp - sum(xp_for_level(l,cfg) for l in range(level))
        needed = xp_for_level(level, cfg)
        rank = await self.get_rank_position(target.id, ctx.guild.id)
        try:
            buf = await render_dlc_card(target, level, xp_in_level, needed, rank, cfg.get("background_url"))
            if buf:
                file = discord.File(buf, filename="rank.png")
                embed = discord.Embed(color=0x7289da)
                embed.set_image(url="attachment://rank.png")
                embed.set_footer(text=f"Aether Guild • Anime Rank #{rank} • Total XP: {total_xp:,}")
                await ctx.send(embed=embed, file=file)
            else:
                embed = discord.Embed(title=f"📊 {target.display_name}", description=f"**Level:** {level}\n**XP:** {xp_in_level}/{needed}\n**Rank:** #{rank}", color=0x7289da)
                embed.set_footer(text=f"Aether Guild • Total XP: {total_xp:,}")
                await ctx.send(embed=embed)
        except Exception:
            log.exception("Operation failed in rank")
            await ctx.send("❌ Rank карт үүсгэхэд алдаа гарлаа. Дахин оролдоно уу.", ephemeral=True)

    @commands.hybrid_command(name="leaderboard", aliases=["levelboard", "levels", "levelleaderboard"], description="Серверийн XP эрэмбийн самбар")
    async def levelboard(self, ctx):
        """Show the XP leaderboard as the shared paginated image card."""
        if ctx.interaction:
            await ctx.defer()
        try:
            board = self.bot.get_cog("Leaderboard")
            if board is None:
                raise RuntimeError("Leaderboard card cog is not loaded")
            view = LeaderboardView(board, ctx, ctx.guild.id)
            file, embed, _state = await view.render_current()
            message = await ctx.send(embed=embed, file=file, view=view) if file else await ctx.send(embed=embed, view=view)
            view.message = message
        except Exception:
            log.exception("Operation failed in levelboard")
            await ctx.send("❌ Level leaderboard уншихад алдаа гарлаа.", ephemeral=True)

    @commands.hybrid_command(name="roles", description="Таны level role-уудыг дахин шалгаж засах")
    @commands.guild_only()
    async def roles(self, ctx):
        target = ctx.author
        if ctx.interaction:
            await ctx.defer(ephemeral=True)
        try:
            granted = await self.sync_level_roles(target)
            await ctx.send(
                f"✅ Level role шалгалт дууслаа. {granted} role нэмэгдлээ.",
                ephemeral=True,
            )
        except Exception:
            log.exception("Operation failed in roles repair")
            await ctx.send("❌ Level role шалгаж чадсангүй.", ephemeral=True)

    @commands.hybrid_command(name="stats", description="Хэрэглэгчийн level, message, voice статистик")
    @commands.guild_only()
    async def stats(self, ctx, user: discord.Member | None = None):
        target = user or ctx.author
        if ctx.interaction:
            await ctx.defer()
        row = await self.bot.db_manager.fetch_one(
            "levels", {"user_id": str(target.id), "guild_id": str(ctx.guild.id)}
        ) or {}
        level = int(row.get("level", 1) or 1)
        xp = int(row.get("xp", 0) or 0)
        messages = int(row.get("message_count", 0) or 0)
        voice_minutes = int(row.get("voice_seconds", 0) or 0) // 60
        rank = await self.get_rank_position(target.id, ctx.guild.id)
        embed = discord.Embed(title=f"📊 {target.display_name} stats", color=INFO_COLOR)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="XP", value=f"{xp:,}", inline=True)
        embed.add_field(name="Rank", value=f"#{rank}", inline=True)
        embed.add_field(name="Messages", value=f"{messages:,}", inline=True)
        embed.add_field(name="Voice", value=f"{voice_minutes:,} минут", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="serveractivity", aliases=["activity"], description="Серверийн идэвхтэй байдлын статистик")
    async def server_activity(self, ctx):
        """Серверийн идэвхтэй байдлыг харах"""
        if ctx.interaction:
            await ctx.defer()
        guild = ctx.guild
        online = sum(1 for m in guild.members if m.status != discord.Status.offline)
        offline = guild.member_count - online
        voice_count = sum(1 for vc in guild.voice_channels for m in vc.members)

        active_chatters = 0
        try:
            lvl_rows = await self.bot.db_manager.fetch_all(
                "levels", {"guild_id": str(guild.id)}
            )
            active_chatters = sum(1 for r in lvl_rows if (r.get("message_count", 0) or 0) > 0)
        except Exception:
            log.exception("Operation failed in server_activity")

        embed = discord.Embed(title=f"📈 {guild.name} - Server Activity", color=SUCCESS_COLOR)
        embed.add_field(name="👥 Members", value=f"Total: {guild.member_count}\nOnline: {online}\nOffline: {offline}")
        embed.add_field(name="🔊 Voice", value=f"Currently in VC: {voice_count}")
        embed.add_field(name="💬 Text Chatters (all-time)", value=active_chatters)
        embed.set_footer(text="Note: Text chatters count is all-time, not 24h. To get 24h stats, add a last_message_time column.")
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Leveling(bot))
