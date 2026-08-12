import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio
import io
import os
import aiohttp
import time
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

# ---------- Төвлөрсөн фонт ----------
try:
    from utils.font_utils import load_font as _load_font
except ImportError:
    def _load_font(size=40, bold=True):
        paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]
        if not bold:
            paths = [p for p in paths if "Bold" not in p and "bd" not in p]
        for p in paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except:
                    pass
        return ImageFont.load_default(size)

# ---------- ProBot палитр ----------
BG_COLOR = (30, 33, 40, 255)
CARD_BG = (44, 47, 51, 255)
BAR_BG = (64, 68, 75, 255)
BAR_FILL = (114, 137, 218, 255)
TEXT_PRIMARY = (255, 255, 255, 255)
TEXT_SECONDARY = (185, 187, 190, 255)
GOLD = (255, 180, 50, 255)
GREEN = (87, 242, 135, 255)
RED = (237, 66, 69, 255)

# ---------- ЭМОЖИ ТОДОРХОЙЛОГЧ ----------
def is_emoji(char):
    cp = ord(char)
    return any(start <= cp <= end for start, end in [
        (0x1F600, 0x1F64F), (0x1F300, 0x1F5FF), (0x1F680, 0x1F6FF),
        (0x1F1E0, 0x1F1FF), (0x2600, 0x26FF), (0x2700, 0x27BF),
        (0x1F900, 0x1F9FF), (0x1FA00, 0x1FA6F), (0x1FA70, 0x1FAFF),
        (0x200D, 0x200D), (0xFE0F, 0xFE0F),
    ])

# ==================== ИНВЕНТАР VIEW ====================
class InventoryView(View):
    def __init__(self, cog, member, all_items, page=0):
        super().__init__(timeout=180)
        self.cog = cog
        self.member = member
        self.all_items = all_items
        self.page = page
        self.per_page = 6
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.member.id:
            await interaction.response.send_message("❌ Энэ товч зөвхөн инвентарын эзэнд зориулагдсан!", ephemeral=True)
            return False
        return True

    async def update_message(self, interaction: discord.Interaction):
        embed, file = await self.cog.build_inventory_embed(self.member, self.all_items, self.page)
        self.prev_button.disabled = (self.page == 0)
        total_pages = max(1, -(-len(self.all_items) // self.per_page))
        self.next_button.disabled = (self.page >= total_pages - 1)
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

    @discord.ui.button(label="🔍 Хэрэглэх", style=discord.ButtonStyle.green, row=0)
    async def use_button(self, interaction: discord.Interaction, button: Button):
        start = self.page * self.per_page
        end = start + self.per_page
        page_items = self.all_items[start:end]
        if not page_items:
            return await interaction.response.send_message("❌ Энэ хуудсанд зүйл байхгүй!", ephemeral=True)

        options = []
        for idx, item in enumerate(page_items):
            label = f"{item['emoji']} {item['name'][:25]} x{item['quantity']}"
            options.append(discord.SelectOption(label=label, value=str(idx)))

        select = Select(placeholder="Хэрэглэх зүйлээ сонгоно уу...", options=options)

        async def select_callback(select_interaction: discord.Interaction):
            idx = int(select.values[0])
            selected = page_items[idx]
            shop = self.cog.bot.get_cog("ShopCog")
            if not shop:
                return await select_interaction.response.send_message("❌ Shop систем олдсонгүй!", ephemeral=True)

            item_id = selected['id']
            if 6000 <= item_id < 7000:
                cafe = self.cog.bot.get_cog("Cafe")
                if not cafe:
                    return await select_interaction.response.send_message("❌ Кафе систем олдсонгүй!", ephemeral=True)
                food_index = item_id - 6000
                if food_index < 0 or food_index >= len(cafe.menu):
                    return await select_interaction.response.send_message("❌ Буруу хоолны ID!", ephemeral=True)
                inv = await shop.get_user_inventory(self.member.id, interaction.guild.id)
                if inv.get(item_id, 0) == 0:
                    return await select_interaction.response.send_message("❌ Танд энэ хоол байхгүй!", ephemeral=True)
                await shop.remove_item(self.member.id, interaction.guild.id, item_id, 1)
                food = cafe.menu[food_index]
                key = f"{self.member.id}_{interaction.guild.id}"
                end_time = time.time() + food['duration']
                cafe.active_buffs[key] = {
                    "type": food['buff'],
                    "end_time": end_time,
                    "xp_mult": food.get('xp_mult', 1),
                    "money_mult": food.get('money_mult', 1),
                }

                quests_cog = self.cog.bot.get_cog("Quests")
                if quests_cog:
                    await quests_cog.trigger_event(self.member.id, interaction.guild.id, "inventory_use", 1)

                await select_interaction.response.send_message(
                    f"🍽️ **{food['emoji']} {food['name']}** идлээ! {food['buff']} ({food['duration']}с)",
                    ephemeral=True
                )
                await self.update_message(interaction)
                return

            if hasattr(shop, 'use_item'):
                success, msg = await shop.use_item(self.member.id, interaction.guild.id, item_id)
                if success:
                    quests_cog = self.cog.bot.get_cog("Quests")
                    if quests_cog:
                        await quests_cog.trigger_event(self.member.id, interaction.guild.id, "inventory_use", 1)

                    await select_interaction.response.send_message(f"✅ {msg}", ephemeral=True)
                    await self.update_message(interaction)
                else:
                    await select_interaction.response.send_message(f"❌ {msg}", ephemeral=True)
            else:
                await select_interaction.response.send_message("❌ Хэрэглэх систем олдсонгүй!", ephemeral=True)

        select.callback = select_callback
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Хэрэглэх зүйлээ сонгоно уу:", view=view, ephemeral=True)

    @discord.ui.button(label="◀ Өмнөх", style=discord.ButtonStyle.gray, row=1)
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        if self.page > 0:
            self.page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Дараах ▶", style=discord.ButtonStyle.gray, row=1)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        total_pages = max(1, -(-len(self.all_items) // self.per_page))
        if self.page < total_pages - 1:
            self.page += 1
            await self.update_message(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass


# ==================== ҮНДСЭН COG ====================
class Cards(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._session: aiohttp.ClientSession = None
        self._bg_cache = {}

    async def cog_load(self):
        self._session = aiohttp.ClientSession()

    async def cog_unload(self):
        if self._session:
            await self._session.close()

    async def _fetch_emoji_image(self, emoji_char, size=28):
        code_points = '-'.join(f'{ord(c):x}' for c in emoji_char)
        url = f"https://cdnjs.cloudflare.com/ajax/libs/twemoji/14.0.2/72x72/{code_points}.png"
        try:
            async with self._session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    img = Image.open(io.BytesIO(data)).convert("RGBA")
                    img = img.resize((size, size), Image.LANCZOS)
                    return img
        except:
            pass
        return None

    async def _draw_text_with_emoji(self, canvas, draw, x, y, text, font, fill, emoji_size=28):
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if is_emoji(ch):
                j = i + 1
                while j < len(text) and (
                    text[j] in ('\u200d', '\ufe0f', '\u20e3') or
                    ('\U0001f3fb' <= text[j] <= '\U0001f3ff')
                ):
                    j += 1
                emoji_seq = text[i:j]
                tokens.append(('emoji', emoji_seq))
                i = j
            else:
                tokens.append(('text', ch))
                i += 1
        cur_x = x
        for typ, val in tokens:
            if typ == 'text':
                draw.text((cur_x, y), val, font=font, fill=fill)
                bbox = draw.textbbox((cur_x, y), val, font=font)
                cur_x += bbox[2] - bbox[0]
            else:
                emoji_img = await self._fetch_emoji_image(val, size=emoji_size)
                if emoji_img:
                    canvas.paste(emoji_img, (cur_x, y - 4), emoji_img)
                    cur_x += emoji_size + 2
                else:
                    draw.text((cur_x, y), val, font=font, fill=fill)
                    bbox = draw.textbbox((cur_x, y), val, font=font)
                    cur_x += bbox[2] - bbox[0]
        return cur_x

    async def _download_avatar(self, url, size):
        try:
            async with self._session.get(url) as resp:
                data = await resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
        except:
            img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    def _find_asset_path(self, asset_name):
        """Assets файлыг олон замаас хайх (cogs/assets/, ./assets/, г.м.)"""
        if not asset_name:
            return None

        candidates = []
        if os.path.isabs(asset_name):
            candidates.append(asset_name)
        else:
            candidates.extend([
                os.path.join(os.path.dirname(__file__), "assets", asset_name),
                os.path.join(os.path.dirname(__file__), asset_name),
                os.path.join(os.getcwd(), "assets", asset_name),
            ])
            if asset_name.startswith("assets"):
                candidates.append(os.path.abspath(asset_name))

        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def _apply_overlay(self, img, overlay_name):
        path = self._find_asset_path(overlay_name)
        if not path:
            return
        try:
            overlay = Image.open(path).convert("RGBA")
            overlay = overlay.resize(img.size, Resampling.LANCZOS)
            img.alpha_composite(overlay)
        except Exception as e:
            # Алдааг үл тоомсорлох
            pass

    async def _load_background(self, guild_id, bg_url):
        if not bg_url:
            return None
        if guild_id in self._bg_cache:
            return self._bg_cache[guild_id]

        img = None
        if isinstance(bg_url, str) and bg_url.startswith(("http://", "https://")):
            try:
                async with self._session.get(bg_url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        img = Image.open(io.BytesIO(data)).convert("RGBA")
            except:
                pass
        else:
            path = self._find_asset_path(bg_url)
            if path:
                try:
                    img = Image.open(path).convert("RGBA")
                except:
                    pass

        if img:
            self._bg_cache[guild_id] = img
        return img

    async def _gather_user_data(self, member, guild):
        eco = self.bot.get_cog("Economy")
        lvl = self.bot.get_cog("Leveling")
        if not eco or not lvl:
            return None

        guild_id = guild.id
        cash = await eco.get_balance(member.id, guild_id)
        bank = await eco.get_bank(member.id, guild_id)
        total = cash + bank
        hunger, mood = 0, 0
        try:
            hunger, mood = await eco.get_hunger_mood(member.id, guild_id)
        except:
            pass
        disc_level = 0
        try:
            disc_level = await eco.get_discord_level(member.id, guild_id)
        except:
            pass

        xp, level = 0, 1
        try:
            row = await self.bot.db_manager.fetch_one(
                "levels", {"user_id": str(member.id), "guild_id": str(guild_id)}
            )
            if row:
                xp = row.get("xp", 0) or 0
                level = row.get("level", 1) or 1
        except:
            pass

        next_xp = 100 * level
        try:
            cfg = await lvl.get_config(guild_id)
            next_xp = lvl.xp_for_level(level, cfg)
        except:
            pass

        title, badge = "Энгийн", "⭐"
        try:
            title, badge = lvl.get_rank_info(level)
        except:
            pass

        rank = 1
        try:
            level_rows = await self.bot.db_manager.fetch_all(
                "levels", {"guild_id": str(guild_id)},
                order_by="level", desc=True,
            )
            level_rows.sort(key=lambda r: (r.get("level", 0) or 0, r.get("xp", 0) or 0), reverse=True)
            rank = next((i for i, r in enumerate(level_rows, 1) if str(r.get("user_id")) == str(member.id)), len(level_rows) + 1)
        except:
            pass

        job_emoji, job_name = "💼", "Ажилгүй"
        try:
            _, job = eco.get_job_for_level(disc_level)
            job_emoji = job['emoji']
            job_name = job['name']
        except:
            pass

        drunk_level = 0
        try:
            drunk_row = await self.bot.db_manager.fetch_one(
                "user_drunk", {"user_id": str(member.id), "guild_id": str(guild_id)}
            )
            if drunk_row:
                drunk_level = min(100, drunk_row.get("level", 0) or 0)
        except:
            pass

        url = member.display_avatar.replace(size=256, format="png").url
        ava = await self._download_avatar(url, 100)

        return {
            "xp": xp, "level": level, "next_xp": next_xp, "rank": rank,
            "title": title, "badge": badge, "cash": cash, "bank": bank,
            "total": total, "job_emoji": job_emoji, "job_name": job_name,
            "hunger": hunger, "mood": mood, "drunk": drunk_level,
            "disc_level": disc_level, "ava": ava
        }

    # ═══════════════ PROBOT СТИЛЬТЭЙ ПРОФАЙЛ КАРТ ═══════════════
    async def _render_profile_card(self, member, data, background=None):
        W, H = 800, 250
        RADIUS = 10
        PAD = 15
        AVA_SIZE = 85

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if background:
            bg = background.resize((W, H), Resampling.LANCZOS)
            img.paste(bg, (0, 0), bg)
        else:
            draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG_COLOR)

        # Overlay-уудыг assets-аас татах
        self._apply_overlay(img, "overlay1.png")
        self._apply_overlay(img, "curveborder.png")
        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, outline=(75, 78, 85), width=1)

        ava_x, ava_y = PAD + 10, (H - AVA_SIZE) // 2
        ava_img = data["ava"].resize((AVA_SIZE, AVA_SIZE))
        img.paste(ava_img, (ava_x, ava_y), ava_img)

        ring_size = AVA_SIZE + 6
        ring = Image.new("RGBA", (ring_size, ring_size), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse((0, 0, ring_size-1, ring_size-1), outline=(114, 137, 218), width=3)
        img.paste(ring, (ava_x - 3, ava_y - 3), ring)

        font_name = _load_font(30, bold=True)
        font_sub = _load_font(16, bold=False)
        font_small = _load_font(14, bold=False)
        font_level = _load_font(32, bold=True)

        tx = ava_x + AVA_SIZE + 15
        draw.text((tx, ava_y + 5), member.display_name[:20], font=font_name, fill=TEXT_PRIMARY)
        draw.text((tx, ava_y + 35), f"@{member.name}", font=font_small, fill=TEXT_SECONDARY)

        level_str = f"LVL {data['level']}"
        level_w = draw.textlength(level_str, font=font_level)
        draw.text((W - PAD - 10, ava_y + 5), level_str, font=font_level, fill=BAR_FILL)
        rank_str = f"#{data['rank']}"
        rank_w = draw.textlength(rank_str, font=font_sub)
        draw.text((W - PAD - 10 - rank_w, ava_y + 45), rank_str, font=font_sub, fill=TEXT_SECONDARY)

        bar_x = tx
        bar_y = ava_y + 60
        bar_w = W - bar_x - 80
        bar_h = 14
        progress = data['xp'] / data['next_xp'] if data['next_xp'] else 0
        progress = max(0.0, min(1.0, progress))
        fill_w = int(bar_w * progress)

        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_FILL)

        font_xp = _load_font(13, bold=False)
        draw.text((bar_x + bar_w + 8, bar_y), f"{data['xp']:,} / {data['next_xp']:,}", font=font_xp, fill=TEXT_SECONDARY)

        info_y = bar_y + bar_h + 10
        col1_x = PAD + 10
        col2_x = W // 2 + 10

        await self._draw_text_with_emoji(img, draw, col1_x, info_y, f"💰 Гар: {data['cash']:,}₮", font=font_small, fill=TEXT_PRIMARY)
        await self._draw_text_with_emoji(img, draw, col1_x, info_y + 20, f"🏦 Банк: {data['bank']:,}₮", font=font_small, fill=TEXT_PRIMARY)
        await self._draw_text_with_emoji(img, draw, col1_x, info_y + 40, f"💼 {data['job_emoji']} {data['job_name'][:18]}", font=font_small, fill=TEXT_SECONDARY)

        await self._draw_text_with_emoji(img, draw, col2_x, info_y, f"🍖 Өлсгөлөн: {data['hunger']}/100", font=font_small, fill=TEXT_PRIMARY)
        await self._draw_text_with_emoji(img, draw, col2_x, info_y + 20, f"🔋 Уур: {data['mood']}/100", font=font_small, fill=TEXT_PRIMARY)
        await self._draw_text_with_emoji(img, draw, col2_x, info_y + 40, f"🍺 Согтолт: {data['drunk']}/100", font=font_small, fill=TEXT_SECONDARY)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ═══════════════ ИНВЕНТАР КАРТ ═══════════════
    async def _render_inventory_card(self, member, avatar_img, page_items, used_slots, total_slots, buffs, page, total_pages):
        W, H = 780, 380
        RADIUS = 12
        PAD = 18
        AVA = 45

        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rounded_rectangle([0, 0, W-1, H-1], radius=RADIUS, fill=BG_COLOR)
        self._apply_overlay(img, "overlay1.png")
        self._apply_overlay(img, "curveborder.png")

        font_title = _load_font(26, True)
        font_sub = _load_font(16, False)
        font_small = _load_font(14, False)

        ava_x, ava_y = PAD, 12
        img.paste(avatar_img, (ava_x, ava_y), avatar_img)

        name = member.display_name[:20]
        draw.text((ava_x + AVA + 10, ava_y + 3), f"{name}'s Inventory", font=font_title, fill=TEXT_PRIMARY)
        await self._draw_text_with_emoji(img, draw, ava_x + AVA + 10, ava_y + 30, f"Багтаамж: {used_slots}/{total_slots}", font=font_sub, fill=TEXT_SECONDARY)

        bar_x = ava_x + AVA + 10
        bar_y = ava_y + 52
        bar_w, bar_h = 280, 10
        progress = used_slots / total_slots if total_slots else 0
        fill_w = int(bar_w * progress)
        draw.rounded_rectangle([bar_x, bar_y, bar_x + bar_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_BG)
        if fill_w > 0:
            draw.rounded_rectangle([bar_x, bar_y, bar_x + fill_w, bar_y + bar_h], radius=bar_h//2, fill=BAR_FILL)

        line_y = bar_y + bar_h + 12
        draw.line([(PAD, line_y), (W - PAD, line_y)], fill=BAR_BG, width=2)

        y = line_y + 12
        for item in page_items:
            emoji_str = item.get("emoji", "📦")
            item_name = item["name"][:30]
            qty = item["quantity"]
            await self._draw_text_with_emoji(img, draw, PAD + 8, y, f"{emoji_str} {item_name}  x{qty}", font=font_small, fill=TEXT_PRIMARY)
            y += 24

        if not page_items:
            draw.text((PAD + 8, y), "Цүнх хоосон байна.", font=font_small, fill=TEXT_SECONDARY)

        buff_y = H - 50
        draw.line([(PAD, buff_y - 8), (W - PAD, buff_y - 8)], fill=BAR_BG, width=1)
        await self._draw_text_with_emoji(img, draw, PAD, buff_y, "✨ BUFFS", font=font_sub, fill=GOLD)
        if buffs:
            buff_text = "  |  ".join(b['name'] for b in buffs[:3])
            await self._draw_text_with_emoji(img, draw, PAD, buff_y + 22, buff_text, font=font_small, fill=TEXT_PRIMARY)
        else:
            draw.text((PAD, buff_y + 22), "Идэвхтэй эффект байхгүй", font=font_small, fill=TEXT_SECONDARY)

        draw.text((W - PAD - 70, H - 22), f"{page + 1}/{total_pages}", font=font_small, fill=TEXT_SECONDARY)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    async def build_inventory_embed(self, member, all_items, page=0):
        shop = self.bot.get_cog("ShopCog")
        max_slots = getattr(shop, "max_inventory_slots", 50) if shop else 50
        used_slots = len(all_items)
        buffs = []
        cafe_cog = self.bot.get_cog("Cafe")
        if cafe_cog:
            user_buff = cafe_cog.get_buff(member.id, member.guild.id)
            if user_buff:
                btype = user_buff.get("type", "???")
                remaining_sec = max(0, user_buff.get("end_time", 0) - time.time())
                if remaining_sec > 0:
                    mins, secs = divmod(int(remaining_sec), 60)
                    btype = f"{btype} ({mins}м {secs}с)"
                buffs.append({"name": btype})
        per_page = 6
        total_pages = max(1, -(-len(all_items) // per_page))
        start = page * per_page
        end = start + per_page
        page_items = all_items[start:end]

        url = member.display_avatar.replace(size=128, format="png").url
        avatar_img = await self._download_avatar(url, 45)

        buf = await self._render_inventory_card(member, avatar_img, page_items, used_slots, max_slots, buffs, page, total_pages)
        embed = discord.Embed(color=0x7289da)
        embed.set_image(url="attachment://inventory.png")
        embed.set_footer(text=f"{member.guild.name} • {member.display_name}")
        return embed, discord.File(buf, filename="inventory.png")

    # ═══════════════ КОМАНДУУД ═══════════════
    @commands.command(name='profile', aliases=['pcard'], description="Профайл картаа харах")
    async def profilecard(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        data = await self._gather_user_data(target, ctx.guild)
        if not data:
            eco = self.bot.get_cog("Economy")
            lvl = self.bot.get_cog("Leveling")
            missing = []
            if not eco: missing.append("Economy")
            if not lvl: missing.append("Leveling")
            return await ctx.send(f"❌ Шаардлагатай когууд ачаалагдаагүй байна: {', '.join(missing)}")

        level_cog = self.bot.get_cog("Leveling")
        bg_url = None
        if level_cog:
            try:
                cfg = await level_cog.get_config(ctx.guild.id)
                bg_url = cfg.get("background_url")
            except:
                pass
        background = await self._load_background(ctx.guild.id, bg_url)

        buf = await self._render_profile_card(target, data, background)
        embed = discord.Embed(color=0x7289da)
        embed.set_image(url="attachment://profilecard.png")
        embed.set_footer(text=f"{ctx.guild.name} • {target.display_name}")
        await ctx.send(embed=embed, file=discord.File(buf, filename="profilecard.png"))

    @commands.command(name='inventory', aliases=['inv', 'icard'], description="Инвентар картаа харах")
    async def inventory_card(self, ctx, member: discord.Member = None):
        target = member or ctx.author
        await ctx.defer()
        shop = self.bot.get_cog("ShopCog")
        if not shop:
            return await ctx.send("❌ Shop систем ачаалагдаагүй байна (ShopCog).")
        inv = await shop.get_user_inventory(target.id, ctx.guild.id)
        all_items = []
        for item_id, qty in inv.items():
            item_data = await shop.get_item(item_id)
            if item_data:
                all_items.append({
                    "id": item_id,
                    "name": item_data.get("name", f"Item {item_id}"),
                    "emoji": item_data.get("emoji", "📦"),
                    "quantity": qty,
                    "rarity": item_data.get("rarity", "common"),
                    "category": item_data.get("category", "other"),
                })
        embed, file = await self.build_inventory_embed(target, all_items, 0)
        view = InventoryView(self, target, all_items, 0)
        msg = await ctx.send(embed=embed, file=file, view=view)
        view.message = msg

async def setup(bot):
    await bot.add_cog(Cards(bot))
