import discord
from discord.ext import commands
from discord import ui
import asyncio
import io
import aiohttp
from PIL import Image, ImageDraw

from utils.fonts import (
    load_font as get_font,
    draw_text_with_fallback,
    get_font_manager,
    get_branding_font,
)
from utils.branding import BOT_NAME

# ---------- K/M/B товчлол ----------
def _format_number(num: int) -> str:
    if num >= 1_000_000_000: return f"{num/1_000_000_000:.1f}B"
    if num >= 1_000_000: return f"{num/1_000_000:.1f}M"
    if num >= 1_000: return f"{num/1_000:.1f}K"
    return str(num)

# ---------- Дугуй аватар ----------
async def fetch_avatar_image(session, url, size=64):
    try:
        async with session.get(url) as resp: data = await resp.read()
        img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
    except:
        img = Image.new("RGBA", (size, size), (88,101,242,255))
    mask = Image.new("L", (size, size), 0); draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255); img.putalpha(mask)
    return img

# ---------- XP тооцоолол ----------
def xp_for_level(level: int, cfg: dict = None):
    if cfg is None: cfg = {}
    if cfg.get("prog_type") == "geometric":
        mult = float(cfg.get("prog_step", 1.5))
        return max(1, int(cfg.get("prog_base", 100) * (mult ** level)))
    return max(1, cfg.get("prog_base", 100) + level * int(cfg.get("prog_step", 150)))


# ==================== КАРТ ЗУРАГЧ ====================
CARD_W = 920
HEADER_H = 148
FOOTER_H = 72
ROW_H = 54

MEDAL_COLORS = [
    (255, 202, 58),    # алт
    (176, 190, 197),   # мөнгө
    (205, 127, 50),    # хүрэл
]
ACCENT = (250, 179, 135)       # #fab387
BG_TOP = (26, 28, 44)
BG_BOTTOM = (14, 15, 24)


class CardRenderer:
    """Лидербордын зурган картын дизайн."""

    def __init__(self, guild_name: str):
        self.guild_name = self.clean(guild_name or "")

    @staticmethod
    def clean(text: str) -> str:
        """Ямар ч ашиглах боломжтой font-д байхгүй тэмдэгтийг хасна (tofu box-оос сэргийлнэ)."""
        if not text:
            return ""
        text = text.replace("\u200b", "").replace("\ufe0f", "")
        fm = get_font_manager()
        kept = []
        for ch in text:
            if ch.isspace() or ch.isascii() or ch in ("…",):
                kept.append(ch)
            elif fm.any_font_has_glyph(ch):
                kept.append(ch)
        return " ".join("".join(kept).split())

    def _text(self, draw, xy, text, size, bold=True, fill=(255, 255, 255, 255), right_edge=None):
        """Per-glyph fallback-тай текст; right_edge өгвөл баруун тийш эргүүлж зурна."""
        text = self.clean(text)
        if not text:
            return xy[0]
        font = get_font(size, bold)
        if right_edge is not None:
            try:
                w = draw.textlength(text, font=font)
            except Exception:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
            xy = (int(right_edge - w), xy[1])
        return draw_text_with_fallback(draw, xy, text, font, fill=fill, size=size, bold=bold)

    def _fit(self, draw, text, size, max_w, bold=True):
        text = self.clean(text)
        font = get_font(size, bold)
        try:
            if draw.textlength(text, font=font) <= max_w:
                return text
            while text and draw.textlength(text + "…", font=font) > max_w:
                text = text[:-1]
            return text + "…"
        except Exception:
            return text[:20]

    def _gradient_bg(self, height: int) -> Image.Image:
        base = Image.new("RGB", (CARD_W, height))
        d = ImageDraw.Draw(base)
        for y in range(height):
            t = y / max(1, height - 1)
            col = tuple(int(BG_TOP[k] * (1 - t) + BG_BOTTOM[k] * t) for k in range(3))
            d.line([(0, y), (CARD_W, y)], fill=col)
        img = base.convert("RGBA")
        glow = Image.new("RGBA", (CARD_W, height), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        gd.ellipse((-260, -220, 420, 240), fill=(*ACCENT, 30))
        gd.ellipse((CARD_W - 380, height - 300, CARD_W + 280, height + 200), fill=(137, 180, 250, 24))
        img.alpha_composite(glow)
        return img

    def _rank_badge(self, draw, cx, cy, rank: int):
        r = 17
        color = MEDAL_COLORS[rank] if rank < 3 else (99, 108, 150)
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=(*color, 46),
            outline=(*color, 255),
            width=2,
        )
        label = str(rank + 1)
        font = get_font(17, bold=True)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.text(
            (cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]),
            label, font=font, fill=(*color, 255),
        )

    def _placeholder_avatar(self, size: int, name: str) -> Image.Image:
        img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        d = ImageDraw.Draw(img)
        letter = self.clean(name)[:1].upper() or "?"
        font = get_font(int(size * 0.5), bold=True)
        try:
            bbox = d.textbbox((0, 0), letter, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            ox, oy = (size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]
            d.text((ox, oy), letter, font=font, fill=(235, 238, 255, 255))
        except Exception:
            pass
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    @staticmethod
    def _circular(img: Image.Image, size: int) -> Image.Image:
        img = img.convert("RGBA").resize((size, size))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    async def render(self, entries, title_text, page: int) -> discord.File:
        """entries: [(uid, name, label, avatar_img | None)]"""
        n = max(len(entries), 3)
        H = HEADER_H + n * ROW_H + FOOTER_H
        img = self._gradient_bg(H)
        draw = ImageDraw.Draw(img)

        # ─── Header ───
        title = self.clean(title_text) or "ЛИДЕРБОРД"
        font_title = get_font(34, bold=True)
        tb = draw.textbbox((0, 0), title, font=font_title)
        draw_text_with_fallback(
            draw, ((CARD_W - (tb[2] - tb[0])) // 2 - tb[0], 34),
            title, font_title, fill=(*ACCENT, 255), size=34, bold=True,
        )
        bar_w = 320
        bx = (CARD_W - bar_w) // 2
        for i in range(bar_w):
            t = i / bar_w
            k = 0.35 + 0.65 * (1 - abs(t - 0.5) * 2)
            col = tuple(int(c * k) for c in ACCENT)
            draw.line([(bx + i, 92), (bx + i, 95)], fill=(*col, 230))

        sub = f"{self.guild_name} • Хуудас {page + 1}" if self.guild_name else f"Хуудас {page + 1}"
        self._text(draw, (0, 108), sub, 18, bold=False, fill=(166, 173, 200, 220))

        # ─── Мөрийн дэвсгэрүүд (нэг давхаргад нь зурж composite хийнэ) ───
        overlay = Image.new("RGBA", (CARD_W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        ys = []
        y = HEADER_H - 6
        for i in range(len(entries)):
            y += ROW_H - 8
            ys.append(y)
            top3 = i < 3
            medal = MEDAL_COLORS[i] if top3 else (120, 130, 170)
            bg_fill = (52, 56, 88, 205) if top3 else (40, 43, 66, 165)
            od.rounded_rectangle(
                (28, y + 4, CARD_W - 28, y + ROW_H - 8),
                radius=13, fill=(0, 0, 0, 70),
            )
            od.rounded_rectangle(
                (28, y, CARD_W - 28, y + ROW_H - 12),
                radius=13, fill=bg_fill,
                outline=(*medal, 110 if top3 else 45), width=1,
            )
            if top3:
                od.rounded_rectangle((31, y + 8, 37, y + ROW_H - 20), radius=3, fill=(*medal, 255))
        img.alpha_composite(overlay)
        draw = ImageDraw.Draw(img)

        # ─── Мөрийн агуулга ───
        name_max_w = int(CARD_W * 0.40)
        ava_size = 38
        for i, (uid, name, label, avatar) in enumerate(entries):
            y = ys[i]
            medal = MEDAL_COLORS[i] if i < 3 else (120, 130, 170)
            cy = y + (ROW_H - 12) // 2
            self._rank_badge(draw, 62, cy, i)

            ax, ay = 92, y + (ROW_H - 12 - ava_size) // 2 + 2
            if avatar is not None:
                img.paste(avatar.resize((ava_size, ava_size)), (ax + 3, ay + 3), avatar.resize((ava_size, ava_size)))
                ring = Image.new("RGBA", (ava_size + 6, ava_size + 6), (0, 0, 0, 0))
                ImageDraw.Draw(ring).ellipse((0, 0, ava_size + 5, ava_size + 5), outline=(*medal, 190), width=2)
                img.alpha_composite(ring, (ax, ay))
            else:
                ph = self._placeholder_avatar(ava_size, name)
                img.paste(ph, (ax + 3, ay + 3), ph)
            draw = ImageDraw.Draw(img)

            self._text(draw, (148, y + 9), self._fit(draw, name, 21, name_max_w),
                       21, bold=True, fill=(240, 243, 255, 255))
            if label:
                self._text(draw, (0, y + 11), label, 19, bold=False,
                           fill=(*ACCENT, 240) if i < 3 else (196, 203, 226, 235),
                           right_edge=CARD_W - 48)

        # ─── Footer ───
        fy = H - FOOTER_H + 18
        draw.line([(40, fy - 10), (CARD_W - 40, fy - 10)], fill=(70, 76, 110, 160), width=1)
        brand_font = get_branding_font(20)
        brand = self.clean(BOT_NAME)
        bb = draw.textbbox((0, 0), brand or "A", font=brand_font)
        bw = bb[2] - bb[0]
        draw_text_with_fallback(
            draw, ((CARD_W - bw) // 2 - bb[0], fy), brand,
            brand_font, fill=(200, 205, 230, 210), size=20, bold=True,
        )

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return discord.File(buf, filename="leaderboard_card.png")


# ==================== VIEW ====================
class LeaderboardView(ui.View):
    PAGE_SIZE = 10

    def __init__(self, cog, ctx, guild_id):
        super().__init__(timeout=300)
        self.cog = cog; self.ctx = ctx; self.guild_id = guild_id
        self.current_category = "level"; self.page = 0
        self.message = None

    # ---------- Өгөгдөл ----------
    async def fetch_category_data(self, limit=10, offset=0):
        """Тухайн төрлөөр эрэмбэлэгдсэн өгөгдөл, гарчиг, шошго функцийг буцаана"""
        cat = self.current_category
        if cat == "level":
            rows = await self.cog.get_top_levels(self.guild_id, limit, offset)
            return rows, "🏆 ТҮВШНИЙ ЛИДЕРБОРД", lambda lvl, xp: f"Түв.{lvl} • {_format_number(xp)} XP"
        elif cat == "messages":
            rows = await self.cog.get_top_messages(self.guild_id, limit, offset)
            return [(uid, cnt) for uid, cnt in rows], "💬 МЕССЕЖИЙН ЛИДЕРБОРД", lambda cnt: f"{_format_number(cnt)} мессеж"
        elif cat == "voice_time":
            rows = await self.cog.get_top_voice(self.guild_id, limit, offset)
            def voice_label(sec):
                h = sec // 3600
                m = (sec % 3600) // 60
                return f"{h} цаг {m} мин"
            return [(uid, sec) for uid, sec in rows], "🎤 ДУУТ ЦАГИЙН ЛИДЕРБОРД", voice_label
        elif cat == "reactions":
            rows = await self.cog.get_top_reactions(self.guild_id, limit, offset)
            return [(uid, cnt) for uid, cnt in rows], "❤️ РЕАКЦЫН ЛИДЕРБОРД", lambda cnt: f"{_format_number(cnt)} реакц"
        elif cat == "money":
            eco = self.ctx.bot.get_cog("Economy")
            if eco and hasattr(eco, "get_top_balances"):
                rows = await eco.get_top_balances(self.guild_id, limit, offset)
                return rows, "💰 ВАЛЮТЫН ЛИДЕРБОРД", lambda bal: f"{_format_number(bal)} ₮"
            return None, None, None
        elif cat == "invites":
            inv = self.ctx.bot.get_cog("InviteTracker")
            if inv and hasattr(inv, "get_top_inviters"):
                rows = await inv.get_top_inviters(self.guild_id, limit, offset)
                return rows, "📨 УРИЛГЫН ЛИДЕРБОРД", lambda cnt: f"{_format_number(cnt)} урилга"
            return None, None, None
        elif cat == "counting":
            cnt = self.ctx.bot.get_cog("Counting")
            if cnt and hasattr(cnt, "get_top_counters"):
                rows = await cnt.get_top_counters(self.guild_id, limit, offset)
                return rows, "🔢 ТООЛОЛТЫН ЛИДЕРБОРД", lambda c: f"{_format_number(c)} зөв тоололт"
            return None, None, None
        elif cat == "games":
            g = self.ctx.bot.get_cog("Games")
            if g and hasattr(g, "get_top_games"):
                rows = await g.get_top_games(self.guild_id, limit, offset)
                return rows, "🎮 ТОГЛООМЫН ЛИДЕРБОРД", lambda sc: f"{_format_number(sc)} ₮ хожил"
            return None, None, None
        return None, None, None

    # ---------- Карт үүсгэх ----------
    async def render_current(self):
        """Одоогийн категори/хуудасны карт буцаана: (file | None, embed, state)
        state: 'ok' | 'empty' | 'unavailable'"""
        offset = self.page * self.PAGE_SIZE
        rows, title, label_func = await self.fetch_category_data(limit=self.PAGE_SIZE, offset=offset)

        if rows is None:
            return None, discord.Embed(
                description="❌ Энэ төрөл одоогоор ажиллахгүй байна (шаардлагатай модуль олдсонгүй).",
                color=0xff0000,
            ), "unavailable"
        if not rows:
            return None, discord.Embed(
                description="Энэ төрөлд өгөгдөл байхгүй.",
                color=0xff0000,
            ), "empty"

        renderer = CardRenderer(self.ctx.guild.name)
        entries = []
        async with aiohttp.ClientSession() as session:
            for row in rows[:self.PAGE_SIZE]:
                uid = int(row[0])
                values = tuple(row[1:])
                member = self.ctx.guild.get_member(uid)
                if not member:
                    try: member = await self.ctx.bot.fetch_user(uid)
                    except: member = None
                name = member.display_name if member else f"ID {uid}"

                if callable(label_func):
                    label = label_func(*values) if len(values) > 1 else label_func(values[0])
                else:
                    label = str(values[0])

                avatar = None
                url = None
                try:
                    if member and member.display_avatar:
                        url = member.display_avatar.replace(size=128, format="png").url
                except Exception:
                    url = None

                cache_key = (uid, url or "")
                cached = self.cog._avatar_cache.get(cache_key)
                if cached is not None:
                    avatar = cached
                elif url:
                    try:
                        avatar = await fetch_avatar_image(session, url, size=76)
                        if len(self.cog._avatar_cache) > 256:
                            self.cog._avatar_cache.clear()
                        self.cog._avatar_cache[cache_key] = avatar
                    except Exception:
                        avatar = None

                entries.append((uid, name, label, avatar))

        file = await renderer.render(entries, title, self.page)
        embed = discord.Embed(color=0x2f3136)
        embed.set_image(url="attachment://leaderboard_card.png")
        return file, embed, "ok"

    async def _refresh_panel(self, interaction: discord.Interaction):
        try:
            file, embed, state = await self.render_current()
        except Exception as e:
            await interaction.edit_original_response(
                embed=discord.Embed(description=f"❌ Карт үүсгэж чадсангүй: {e}", color=0xff0000),
                view=self,
            )
            return
        if file:
            await interaction.edit_original_response(embed=embed, attachments=[], attachment=file, view=self)
            return
        # Хоосон хуудас руу орсон бол эхний хуудас руу нэг удаа буцаж зурна
        if state == "empty" and self.page > 0:
            self.page = 0
            await self._refresh_panel(interaction)
            return
        await interaction.edit_original_response(embed=embed, attachments=[], view=self)

    # ---------- Интерактууд ----------
    @ui.select(placeholder="Лидербордын төрөл сонгох", options=[
        discord.SelectOption(label="🏆 Түвшин", value="level", description="Түвшнээр эрэмбэлэх", default=True),
        discord.SelectOption(label="💬 Мессеж", value="messages", description="Илгээсэн мессежийн тоогоор"),
        discord.SelectOption(label="🎤 Дуут цаг", value="voice_time", description="Дуут сувагт зарцуулсан хугацаа"),
        discord.SelectOption(label="❤️ Реакц", value="reactions", description="Реакц дарах тоогоор"),
        discord.SelectOption(label="💰 Мөнгө", value="money", description="Валютын хэмжээгээр"),
        discord.SelectOption(label="📨 Урилга", value="invites", description="Урилгын тоогоор"),
        discord.SelectOption(label="🔢 Тоололт", value="counting", description="Counting тоглоомын зөв тоололт"),
        discord.SelectOption(label="🎮 Тоглоом", value="games", description="Тоглоомын ялалт/хожил"),
    ])
    async def category_select(self, interaction, select):
        self.current_category = select.values[0]
        self.page = 0
        for opt in select.options:
            opt.default = (opt.value == self.current_category)
        await interaction.response.defer()
        await self._refresh_panel(interaction)

    @ui.button(label="◀️", style=discord.ButtonStyle.secondary, row=1)
    async def prev_page(self, interaction, button):
        if self.page > 0:
            self.page -= 1
            await interaction.response.defer()
            await self._refresh_panel(interaction)
        else:
            await interaction.response.send_message("Эхний хуудасан дээр байна.", ephemeral=True)

    @ui.button(label="▶️", style=discord.ButtonStyle.secondary, row=1)
    async def next_page(self, interaction, button):
        self.page += 1
        await interaction.response.defer()
        await self._refresh_panel(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


# ==================== MAIN COG ====================
class Leaderboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._avatar_cache = {}

    async def cog_load(self):
        # Font cmap-уудыг дэвсгэрт урьдчилан уншиж эхний картыг хурдасгана
        try:
            asyncio.get_running_loop().create_task(asyncio.to_thread(self._warm_font_cache))
        except Exception:
            pass

    @staticmethod
    def _warm_font_cache():
        try:
            fm = get_font_manager()
            for path, _bold in fm._discover_fonts():
                fm._get_cmap(path)
        except Exception:
            pass

    # ── DB queries ──
    async def get_top_levels(self, guild_id, limit=10, offset=0):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="level", desc=True, limit=limit, offset=offset,
        )
        rows.sort(key=lambda r: (r.get("level", 0) or 0, r.get("xp", 0) or 0), reverse=True)
        return [(r["user_id"], r.get("level", 1) or 1, r.get("xp", 0) or 0) for r in rows]

    async def get_top_messages(self, guild_id, limit=10, offset=0):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="message_count", desc=True, limit=limit, offset=offset,
        )
        return [(r["user_id"], r.get("message_count", 0) or 0) for r in rows]

    async def get_top_voice(self, guild_id, limit=10, offset=0):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="voice_seconds", desc=True, limit=limit, offset=offset,
        )
        return [(r["user_id"], r.get("voice_seconds", 0) or 0) for r in rows]

    async def get_top_reactions(self, guild_id, limit=10, offset=0):
        rows = await self.bot.db_manager.fetch_all(
            "levels", {"guild_id": str(guild_id)},
            order_by="reaction_count", desc=True, limit=limit, offset=offset,
        )
        return [(r["user_id"], r.get("reaction_count", 0) or 0) for r in rows]

    @commands.hybrid_command(name="leaderboard", aliases=["lb"], description="Серверийн эрэмбийн самбар")
    async def leaderboard_cmd(self, ctx):
        await ctx.defer()
        view = LeaderboardView(self, ctx, ctx.guild.id)
        try:
            file, embed, _state = await view.render_current()
        except Exception as e:
            file, embed = None, discord.Embed(
                description=f"❌ Карт үүсгэж чадсангүй: {e}", color=0xff0000,
            )
        if file:
            msg = await ctx.send(embed=embed, file=file, view=view)
        else:
            msg = await ctx.send(embed=embed, view=view)
        view.message = msg


async def setup(bot):
    await bot.add_cog(Leaderboard(bot))
