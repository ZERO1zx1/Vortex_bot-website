import discord
from discord.ext import commands
from discord.ui import View, Button, Select
import asyncio
import io
import logging
import os
import aiohttp
import time
from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

logger = logging.getLogger(__name__)

# ---------- Centralized Unicode-aware font management ----------
from src.utils.fonts import (
    load_font as _load_font,
    is_emoji,
    draw_text_with_fallback,
    get_font_manager,
)

# ---------- Explorer-journal art kit (procedural illustrated style) ----------
from src.utils import journal_style as journal

# Embed accent matching the parchment pages.
JOURNAL_EMBED_COLOR = 0xC89A3D

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

    async def update_message(self, interaction: discord.Interaction = None):
        embed, file = await self.cog.build_inventory_embed(self.member, self.all_items, self.page)
        self.prev_button.disabled = (self.page == 0)
        total_pages = max(1, -(-len(self.all_items) // self.per_page))
        self.next_button.disabled = (self.page >= total_pages - 1)
        # Панел мессежийг шууд засах (select-ийн ephemeral хариултыг будлиулгүйн тулд)
        # NOTE: Message.edit() нь `attachments` авдаг, `files` гэсэн параметр байхгүй.
        if self.message:
            try:
                await self.message.edit(embed=embed, attachments=[file], view=self)
                return
            except discord.HTTPException as e:
                logger.debug("inventory panel edit failed, falling back: %s", e)
        if interaction is not None:
            target_msg = self.message or getattr(interaction, "message", None)
            if target_msg is not None:
                try:
                    await target_msg.edit(embed=embed, attachments=[file], view=self)
                    return
                except discord.HTTPException as e:
                    logger.debug("inventory panel edit failed, falling back: %s", e)
            await interaction.followup.send(embed=embed, file=file, view=self, ephemeral=True)

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
            except discord.HTTPException as e:
                logger.debug("inventory view timeout edit failed: %s", e)


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
        except (aiohttp.ClientError, OSError) as e:
            logger.debug("emoji fetch failed for %r: %s", emoji_char, e)
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

        # Group adjacent text tokens into runs for per-glyph fallback
        runs = []
        current_text = ""
        for typ, val in tokens:
            if typ == 'text':
                current_text += val
            else:
                if current_text:
                    runs.append(('text', current_text))
                    current_text = ""
                runs.append(('emoji', val))
        if current_text:
            runs.append(('text', current_text))

        cur_x = x
        font_size = getattr(font, 'size', 20)
        for typ, val in runs:
            if typ == 'text':
                # Use per-glyph Unicode fallback for text runs
                cur_x = draw_text_with_fallback(
                    draw, (cur_x, y), val, font, fill=fill,
                    size=font_size, bold=False
                )
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
        except (aiohttp.ClientError, OSError) as e:
            logger.debug("avatar download failed, using fallback: %s", e)
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

        equip_emojis = ""
        try:
            shop = self.bot.get_cog("ShopCog")
            if shop and hasattr(shop, "get_equips"):
                equips = await shop.get_equips(member.id, guild_id)
                if equips:
                    equip_emojis = " ".join(i["emoji"] for i in equips.values())
        except:
            pass

        url = member.display_avatar.replace(size=256, format="png").url
        ava = await self._download_avatar(url, 100)

        return {
            "xp": xp, "level": level, "next_xp": next_xp, "rank": rank,
            "title": title, "badge": badge, "cash": cash, "bank": bank,
            "total": total, "job_emoji": job_emoji, "job_name": job_name,
            "hunger": hunger, "mood": mood, "drunk": drunk_level,
            "disc_level": disc_level, "ava": ava, "equips": equip_emojis
        }

    # ═══════════════ EXPLORER'S JOURNAL ПРОФАЙЛ ХУУДАС ═══════════════
    async def _render_profile_card(self, member, data, background=None):
        W, H = 820, 348
        seed = abs(hash(getattr(member, "id", 7))) % 997

        img = journal.parchment((W, H), seed=seed)
        # Хувийн фон (background_url) байвал цаасны дээр бүдэгхэн шингээх
        if background:
            try:
                bg = background.convert("RGBA").resize((W, H), Resampling.LANCZOS)
                img = Image.blend(bg, img, 0.55)
            except Exception as e:
                logger.debug("profile background skipped: %s", e)
        draw = ImageDraw.Draw(img)
        journal.ink_border(draw, (W, H), seed=seed)

        font_name = _load_font(30, bold=True)
        font_small = _load_font(14, bold=False)
        font_seal = _load_font(20, bold=True)

        # Зүүн талд хавчуулсан хөрөг
        journal.sketch_frame(img, (48, 100, 144, 196), data["ava"], seed=seed)
        draw = ImageDraw.Draw(img)  # sketch_frame зурсны дараа дахин авах

        # Нэрийн тууз
        journal.banner(draw, (176, 24, 596, 64), member.display_name[:20], font_name, seed=seed)
        uname_line = f"@{member.name}"
        if data.get("equips"):
            uname_line += f"  {data['equips']}"
        await self._draw_text_with_emoji(img, draw, 184, 70, uname_line, font=font_small, fill=journal.INK_SOFT)

        # Түвшний лав тамга
        journal.wax_seal(draw, (736, 66), 46, f"LVL {data['level']}", font_seal, seed=seed)
        # Зэрэглэлийн нөхөөс (embroidered patch)
        journal.patch(draw, (628, 122, 792, 156))
        rank_txt = f"#{data['rank']} • {data.get('title', '')[:14]}"
        try:
            rtw = draw.textlength(rank_txt, font=font_small)
        except AttributeError:
            rtw = draw.textsize(rank_txt, font=font_small)[0]
        draw.text(((628 + 792 - rtw) / 2, 131), rank_txt, font=font_small, fill=journal.INK)

        # Туршлагын усан будгийн зам
        progress = data['xp'] / data['next_xp'] if data['next_xp'] else 0
        journal.watercolor_bar(draw, (48, 216, 640, 240), progress,
                               journal.LEAF, journal.RIVER, seed=seed)
        xp_txt = f"{data['xp']:,} / {data['next_xp']:,} XP"
        draw.text((650, 218), xp_txt, font=font_small, fill=journal.INK_SOFT)

        # Тусгаарлах зураас + хоёр баганатай үзүүлэлт
        journal.sketch_divider(draw, 48, 772, 256, seed=seed)
        col1_x, col2_x = 60, 430
        info_y = 266
        await self._draw_text_with_emoji(img, draw, col1_x, info_y, f"💰 Гар: {data['cash']:,}₮", font=font_small, fill=journal.INK)
        await self._draw_text_with_emoji(img, draw, col1_x, info_y + 22, f"🏦 Банк: {data['bank']:,}₮", font=font_small, fill=journal.INK)
        await self._draw_text_with_emoji(img, draw, col1_x, info_y + 44, f"💼 {data['job_emoji']} {data['job_name'][:16]}", font=font_small, fill=journal.INK_SOFT)
        await self._draw_text_with_emoji(img, draw, col2_x, info_y, f"🍖 Өлсгөлөн: {data['hunger']}/100", font=font_small, fill=journal.INK)
        await self._draw_text_with_emoji(img, draw, col2_x, info_y + 22, f"🔋 Уур: {data['mood']}/100", font=font_small, fill=journal.INK)
        await self._draw_text_with_emoji(img, draw, col2_x, info_y + 44, f"🍺 Согтолт: {data['drunk']}/100", font=font_small, fill=journal.INK_SOFT)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        buf.seek(0)
        return buf

    # ═══════════════ CROSS-HATCHED SATCHEL ИНВЕНТАР ═══════════════
    async def _render_inventory_card(self, member, avatar_img, page_items, used_slots, total_slots, buffs, page, total_pages):
        W, H = 800, 440
        seed = abs(hash(getattr(member, "id", 7))) % 997

        img = journal.parchment((W, H), seed=seed)
        draw = ImageDraw.Draw(img)
        journal.ink_border(draw, (W, H), seed=seed)

        font_title = _load_font(24, True)
        font_sub = _load_font(15, False)
        font_small = _load_font(13, False)

        # Толгой: хөрөг + тууз + багтаамжийн зам
        journal.sketch_frame(img, (40, 28, 85, 73), avatar_img, seed=seed)
        draw = ImageDraw.Draw(img)
        journal.banner(draw, (104, 24, 480, 60), f"{member.display_name[:18]}'s Satchel", font_title, seed=seed)
        cap_txt = f"Багтаамж: {used_slots}/{total_slots}"
        await self._draw_text_with_emoji(img, draw, 500, 30, cap_txt, font=font_sub, fill=journal.INK_SOFT)
        journal.watercolor_bar(draw, (500, 52, 740, 66), used_slots / total_slots if total_slots else 0,
                               journal.GOLD, journal.WAX_RED, seed=seed)

        # 3x2 нүд: зүйл бүр — crosshatch дэвсгэр, дүрс, нэр, тооны зураас, rarity шошго
        cols, rows = 3, 2
        gx, gy, gw, gh, gap = 40, 96, 232, 128, 12
        for idx in range(cols * rows):
            sx = gx + (idx % cols) * (gw + gap)
            sy = gy + (idx // cols) * (gh + gap)
            journal.patch(draw, (sx, sy, sx + gw, sy + gh))
            journal.crosshatch(draw, (sx + 8, sy + 8, sx + gw - 8, sy + gh - 8),
                               spacing=9, fill=(60, 46, 30, 46))
            if idx >= len(page_items):
                draw.text((sx + 70, sy + 52), "— хоосон —", font=font_small, fill=journal.INK_FAINT)
                continue
            item = page_items[idx]
            emoji_img = await self._fetch_emoji_image(item.get("emoji", "📦"), size=44)
            if emoji_img:
                img.paste(emoji_img, (sx + 14, sy + 14), emoji_img)
            draw.text((sx + 66, sy + 10), item["name"][:17], font=font_sub, fill=journal.INK)
            qty = item["quantity"]
            used = journal.tally(draw, sx + 66, sy + 34, qty)
            if not used:  # Том овоолгыг товч тэмдэглэгээгээр
                draw.text((sx + 66, sy + 34), f"x{qty}", font=font_sub, fill=journal.INK)
            rarity = str(item.get("rarity", "common")).lower()
            journal.twine_tag(draw, sx + 64, sy + 66, rarity, font_small,
                              journal.RARITY_COLORS.get(rarity, journal.RARITY_COLORS["common"]))
            draw.text((sx + gw - 52, sy + gh - 22), f"ID:{item.get('id', '?')}",
                      font=font_small, fill=journal.INK_FAINT)

        if not page_items:
            draw.text((gx + 8, gy + 8), "Цүнх хоосон байна.", font=font_small, fill=journal.INK_SOFT)

        # Доод талд: шохойн самбар дээрх идэвхтэй эффектүүд + хуудас
        journal.chalk_panel(draw, (40, H - 56, 660, H - 24), seed=seed)
        if buffs:
            buff_text = "  |  ".join(b['name'] for b in buffs[:2])[:52]
        else:
            buff_text = "Идэвхтэй эффект байхгүй"
        await self._draw_text_with_emoji(img, draw, 52, H - 50, f"✨ {buff_text}",
                                         font=font_small, fill=journal.CHALK)
        draw.text((684, H - 48), f"{page + 1}/{total_pages}", font=font_small, fill=journal.INK_SOFT)

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
        embed = discord.Embed(color=JOURNAL_EMBED_COLOR)
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
        embed = discord.Embed(color=JOURNAL_EMBED_COLOR)
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
