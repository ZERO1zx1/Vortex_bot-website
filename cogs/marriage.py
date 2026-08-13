from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands, ui
from discord.ui import View, Button
from utils.supabase_cog import SupabaseCog
from discord import ButtonStyle
import time
import datetime
from typing import Optional
import asyncio
import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont

# ---------- Centralized Unicode-aware font management ----------
from utils.fonts import load_font as _load_font

# ══════════════ ӨНГӨНҮҮД ══════════════
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
PURPLE_COLOR = 0xcba6f7
LOVE_COLOR = 0xff69b4
INFO_COLOR = 0x89b4fa

PROPOSAL_TIMEOUT = 120

GIFTS = {
    "flower":    {"name": "🌹 Цэцэг",        "emoji": "🌹", "love": 5},
    "chocolate": {"name": "🍫 Шоколад",     "emoji": "🍫", "love": 10},
    "ring":      {"name": "💍 Бөгж",        "emoji": "💍", "love": 50},
    "necklace":  {"name": "📿 Зүүлт",       "emoji": "📿", "love": 30},
    "teddy":     {"name": "🧸 Тедди",       "emoji": "🧸", "love": 15},
}

# ══════════════ VIEWS ══════════════
class ProposalView(View):
    def __init__(self, cog, guild_id, proposer_id, target_id, ring_name, ring_emoji, ring_item_id):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id
        self.proposer_id = proposer_id
        self.target_id = target_id
        self.ring_name = ring_name
        self.ring_emoji = ring_emoji
        self.ring_item_id = ring_item_id
        self.message = None

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        guild = interaction.guild
        proposer = guild.get_member(self.proposer_id)
        if not proposer:
            return await interaction.response.send_message("❌ Санал тавьсан хүн серверээс гарсан.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.cog.add_marriage(self.guild_id, self.proposer_id, self.target_id, self.ring_name, self.ring_emoji)
        shop = self.cog.bot.get_cog("ShopCog")
        if shop and self.ring_item_id:
            await shop.remove_item(self.proposer_id, self.guild_id, self.ring_item_id, 1)

        await self.cog.announce_marriage(guild, proposer, interaction.user)
        await self.cog.grant_marriage_role(guild, proposer)
        await self.cog.grant_marriage_role(guild, interaction.user)

        embed = discord.Embed(
            title="💒 ГЭРЛЭЛТ БҮРТГЭГДЛЭЭ!",
            description=f"{proposer.mention} болон {interaction.user.mention} гэрлэлээ!\n💍 Бөгж: {self.ring_emoji} {self.ring_name}",
            color=LOVE_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        proposer = interaction.guild.get_member(self.proposer_id)
        embed = discord.Embed(
            title="💔 ТАТГАЛЗСАН",
            description=f"{interaction.user.mention} {proposer.mention if proposer else 'хэрэглэгч'}-ийн саналаас татгалзлаа.",
            color=ERROR_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except: pass

class AdoptView(View):
    def __init__(self, bot, guild_id, parent_id, child_id, proposal_type="adoption"):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.bot = bot
        self.guild_id = guild_id
        self.parent_id = parent_id
        self.child_id = child_id
        self.proposal_type = proposal_type
        self.message = None

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.child_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.bot.db_manager.delete(
            "marriage_proposals",
            {"guild_id": str(self.guild_id), "to_id": str(self.child_id), "proposal_type": self.proposal_type},
        )
        await self.bot.db_manager.insert("adoptions", {
            "guild_id": str(self.guild_id),
            "parent_id": str(self.parent_id),
            "child_id": str(self.child_id),
            "type": self.proposal_type,
            "adopted_since": int(time.time()),
        })
        parent = interaction.guild.get_member(self.parent_id)
        embed = discord.Embed(
            title="👨‍👧‍👦 ӨРГӨМЖЛӨЛТ БАТЛАГДЛАА" if self.proposal_type=="adoption" else "👪 ЭЦЭГ ЭХ БОЛЛОО",
            description=f"{parent.mention if parent else 'Хэрэглэгч'} {interaction.user.mention}-г {'хүүхэд' if self.proposal_type=='adoption' else 'эцэг эх'} болгон {'өргөмжлөв' if self.proposal_type=='adoption' else 'сонгов'}!",
            color=SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.child_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.bot.db_manager.delete(
            "marriage_proposals",
            {"guild_id": str(self.guild_id), "to_id": str(self.child_id), "proposal_type": self.proposal_type},
        )
        embed = discord.Embed(title="👶 ТАТГАЛЗСАН", description=f"{interaction.user.mention} саналаас татгалзлаа.", color=WARNING_COLOR)
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except: pass

# ══════════════ АДМИН САМБАР ══════════════
class MarriageSetupView(View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        cfg = await self.cog.get_guild_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        embed = discord.Embed(title="💍 Гэрлэлтийн тохиргоо", color=PURPLE_COLOR)
        embed.add_field(name="🔘 Систем", value="✅ Идэвхтэй" if cfg["enabled"] else "❌ Унтарсан", inline=True)
        embed.add_field(name="❤️ Полигами", value="✅ Зөвшөөрөгдсөн" if cfg["polygamy"] else "❌ Хориотой", inline=True)
        embed.add_field(name="👥 Хамгийн их гэрлэлт", value=f"{cfg['max_spouses']}", inline=True)
        channel = guild.get_channel(cfg.get("announce_channel", 0))
        embed.add_field(name="📢 Мэдэгдэл суваг", value=channel.mention if channel else "Тохируулаагүй", inline=False)
        role = guild.get_role(cfg.get("marriage_role", 0))
        embed.add_field(name="💑 Гэрлэлтийн роль", value=role.mention if role else "Тохируулаагүй", inline=False)
        embed.set_footer(text="Дээрх товчнуудаар тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Мэдэгдэл суваг", row=0)
    async def select_channel(self, interaction, select: ui.ChannelSelect):
        await self.cog.set_guild_config(self.guild_id, announce_channel=select.values[0].id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🔘 Систем", style=discord.ButtonStyle.primary, row=1)
    async def toggle_enabled(self, interaction, button):
        cfg = await self.cog.get_guild_config(self.guild_id)
        await self.cog.set_guild_config(self.guild_id, enabled=not cfg["enabled"])
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="❤️ Полигами", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_polygamy(self, interaction, button):
        cfg = await self.cog.get_guild_config(self.guild_id)
        await self.cog.set_guild_config(self.guild_id, polygamy=not cfg["polygamy"])
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="👥 Макс гэрлэлт", style=discord.ButtonStyle.secondary, row=2)
    async def max_spouses_button(self, interaction, button):
        await interaction.response.send_modal(MaxSpousesModal(self))

    @ui.button(label="💑 Роль", style=discord.ButtonStyle.secondary, row=2)
    async def role_button(self, interaction, button):
        await interaction.response.send_modal(MarriageRoleModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction, button):
        await interaction.response.defer()
        await self.refresh(interaction)

class MaxSpousesModal(ui.Modal, title="Хамгийн их гэрлэх тоо"):
    amount = ui.TextInput(label="Тоо", placeholder="1", required=True)
    def __init__(self, view): super().__init__(); self.view = view
    async def on_submit(self, interaction):
        try:
            val = int(self.amount.value)
            if val < 1: raise ValueError
            await self.view.cog.set_guild_config(self.view.guild_id, max_spouses=val)
            await interaction.response.send_message(f"✅ {val}", ephemeral=True)
            await self.view.refresh(interaction)
        except: await interaction.response.send_message("❌ Буруу утга.", ephemeral=True)

class MarriageRoleModal(ui.Modal, title="Гэрлэлтийн роль ID"):
    role_id = ui.TextInput(label="Роль ID", placeholder="123456789", required=True)
    def __init__(self, view): super().__init__(); self.view = view
    async def on_submit(self, interaction):
        try:
            rid = int(self.role_id.value)
            role = interaction.guild.get_role(rid)
            if not role: return await interaction.response.send_message("❌ Роль олдсонгүй.", ephemeral=True)
            await self.view.cog.set_guild_config(self.view.guild_id, marriage_role=rid)
            await interaction.response.send_message(f"✅ {role.mention}", ephemeral=True)
            await self.view.refresh(interaction)
        except: await interaction.response.send_message("❌ Буруу ID.", ephemeral=True)

# ══════════════ ҮНДСЭН COG ══════════════
class Marriage(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    async def init_db(self):
        # Tables are pre-configured in Supabase
        pass

    async def cog_load(self):
        # Tables are pre-configured in Supabase
        pass

    # ═════════ ХЭРЭГЛЭГЧИЙН ФУНКЦУУД ═════════
    async def get_guild_config(self, guild_id):
        row = await self.bot.db_manager.fetch_one("marriage_guild_config", {"guild_id": str(guild_id)})
        if not row:
            return {"enabled": True, "polygamy": False, "max_spouses": 1, "announce_channel": None, "marriage_role": None}
        return {"enabled": bool(row.get("enabled", 1)), "polygamy": bool(row.get("polygamy", 0)),
                "max_spouses": row.get("max_spouses", 1), "announce_channel": row.get("announce_channel"),
                "marriage_role": row.get("marriage_role")}

    async def set_guild_config(self, guild_id, **kwargs):
        gid = str(guild_id)
        data = {"guild_id": gid}
        data.update(kwargs)
        await self.bot.db_manager.upsert("marriage_guild_config", data, on_conflict="guild_id")

    async def grant_marriage_role(self, guild, member):
        cfg = await self.get_guild_config(guild.id)
        if cfg["marriage_role"]:
            role = guild.get_role(cfg["marriage_role"])
            if role and role not in member.roles:
                try: await member.add_roles(role, reason="Гэрлэлт")
                except: pass

    async def remove_marriage_role(self, guild, member):
        cfg = await self.get_guild_config(guild.id)
        if cfg["marriage_role"]:
            role = guild.get_role(cfg["marriage_role"])
            if role and role in member.roles:
                try: await member.remove_roles(role, reason="Салалт")
                except: pass

    async def announce_marriage(self, guild, user1, user2):
        cfg = await self.get_guild_config(guild.id)
        if cfg["announce_channel"]:
            channel = guild.get_channel(cfg["announce_channel"])
            if channel:
                embed = discord.Embed(title="💒 Шинэ гэрлэлт!", description=f"{user1.mention} болон {user2.mention} гэрлэлээ!", color=LOVE_COLOR)
                await channel.send(embed=embed)

    async def announce_divorce(self, guild, user1, user2):
        cfg = await self.get_guild_config(guild.id)
        if cfg["announce_channel"]:
            channel = guild.get_channel(cfg["announce_channel"])
            if channel:
                embed = discord.Embed(title="💔 Салалт", description=f"{user1.mention} болон {user2.mention} саллаа.", color=ERROR_COLOR)
                await channel.send(embed=embed)

    # ═════════ ГЭРЛЭЛТ ═════════
    async def get_marriages(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "marriages", {"guild_id": str(guild_id)}
        )
        result = []
        for r in rows:
            uid = r.get("user_id")
            pid = r.get("partner_id")
            if str(uid) != str(user_id) and str(pid) != str(user_id):
                continue
            partner = pid if str(uid) == str(user_id) else uid
            result.append({"partner": int(partner), "love_points": r.get("love_points", 0) or 0,
                           "ring": f"{r.get('ring_emoji', '')} {r.get('ring_name', '')}".strip() if r.get("ring_emoji") else r.get("ring_name", ""),
                           "ring_name": r.get("ring_name"), "ring_emoji": r.get("ring_emoji", ""),
                           "marriage_date": r.get("marriage_date")})
        return result

    async def add_marriage(self, guild_id, u1, u2, ring_name, ring_emoji=""):
        mar_date = int(time.time())
        for a, b in [(u1, u2), (u2, u1)]:
            await self.bot.db_manager.insert("marriages", {
                "user_id": str(a), "partner_id": str(b), "guild_id": str(guild_id),
                "marriage_date": mar_date, "ring_name": ring_name, "ring_emoji": ring_emoji, "love_points": 0,
            })

    async def remove_marriage(self, guild_id, u1, u2):
        await self.bot.db_manager.delete(
            "marriages",
            {"guild_id": str(guild_id), "user_id": str(u1), "partner_id": str(u2)},
        )
        await self.bot.db_manager.delete(
            "marriages",
            {"guild_id": str(guild_id), "user_id": str(u2), "partner_id": str(u1)},
        )

    async def marriage_exists(self, guild_id, u1, u2):
        row = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(u1), "partner_id": str(u2)}
        )
        if row:
            return True
        row = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(u2), "partner_id": str(u1)}
        )
        return row is not None

    async def get_spouses(self, guild_id, user_id):
        return [m["partner"] for m in await self.get_marriages(guild_id, user_id)]

    # ═════════ ЭЦЭГ ЭХ / ХҮҮХЭД ═════════
    async def get_children(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(user_id)}
        )
        return [int(r["child_id"]) for r in rows]

    async def get_parents(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "adoptions", {"guild_id": str(guild_id), "child_id": str(user_id)}
        )
        return [int(r["parent_id"]) for r in rows]

    async def add_parent_child(self, guild_id, parent_id, child_id, rel_type="adoption"):
        await self.bot.db_manager.upsert(
            "adoptions",
            {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id),
             "type": rel_type, "adopted_since": int(time.time())},
            on_conflict="guild_id,parent_id,child_id",
        )

    async def remove_parent_child(self, guild_id, parent_id, child_id):
        await self.bot.db_manager.delete(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id)}
        )

    async def is_parent_child(self, guild_id, parent_id, child_id):
        row = await self.bot.db_manager.fetch_one(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id)}
        )
        return row is not None

    # ═════════ БЛОК / АВТО ЗӨВШӨӨРӨЛ ═════════
    async def is_blocked(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return bool(row.get("blocked", 0)) if row else False

    async def set_blocked(self, guild_id, user_id, blocked):
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "blocked": int(blocked)},
            on_conflict="guild_id,user_id",
        )

    async def get_auto_accept(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return bool(row.get("auto_accept_marriage", 0)) if row else False

    async def set_auto_accept(self, guild_id, user_id, auto):
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "auto_accept_marriage": int(auto)},
            on_conflict="guild_id,user_id",
        )

    # ═════════ БЭЛЭГ / LOVE ═════════
    async def add_gift(self, guild_id, from_id, to_id, gift_type, love):
        await self.bot.db_manager.insert("marriage_gifts", {
            "guild_id": str(guild_id), "from_id": str(from_id), "to_id": str(to_id),
            "gift_type": gift_type, "love_points": love, "given_at": int(time.time()),
        })
        marriage = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(from_id), "partner_id": str(to_id)}
        )
        if not marriage:
            marriage = await self.bot.db_manager.fetch_one(
                "marriages", {"guild_id": str(guild_id), "user_id": str(to_id), "partner_id": str(from_id)}
            )
        if marriage:
            await self.bot.db_manager.update(
                "marriages",
                {"guild_id": str(guild_id), "user_id": str(from_id), "partner_id": str(to_id)},
                {"love_points": (marriage.get("love_points", 0) or 0) + love},
            )

    async def get_anniversary(self, marriage_date):
        if not marriage_date: return None
        try: marriage_date = int(marriage_date)
        except: return None
        today = datetime.datetime.now().date()
        mar_date = datetime.datetime.fromtimestamp(marriage_date).date()
        days = (today - mar_date).days
        next_ann = datetime.datetime(today.year, mar_date.month, mar_date.day).date()
        if next_ann < today: next_ann = datetime.datetime(today.year + 1, mar_date.month, mar_date.day).date()
        return {"days": days, "next_days": (next_ann - today).days, "date": mar_date.strftime("%Y-%m-%d")}

    async def get_last_gift_time(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return row.get("last_gift_daily", 0) if row else 0

    async def update_last_gift_time(self, guild_id, user_id):
        now = int(time.time())
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "last_gift_daily": now},
            on_conflict="guild_id,user_id",
        )

    async def get_last_love_time(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return row.get("last_love_daily", 0) if row else 0

    async def update_last_love_time(self, guild_id, user_id):
        now = int(time.time())
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "last_love_daily": now},
            on_conflict="guild_id,user_id",
        )

    # ═════════ ЗУРАГ ТАТАХ ═════════
    async def _download_avatar(self, sess, url, size):
        try:
            async with sess.get(url) as resp: data = await resp.read()
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
        except: img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    # ═════════ SLASH COMMANDS (ГРУПП) ═════════
    marriage_group = app_commands.Group(name="marriage", description="Гэрлэлт, гэр бүлийн командууд")

    @marriage_group.command(name="marry", description="Гэрлэх санал тавих")
    @app_commands.describe(user="Гэрлэх санал тавих хэрэглэгч")
    async def slash_marry(self, interaction: discord.Interaction, user: discord.Member):
        await self._propose(interaction, user, is_slash=True)

    @marriage_group.command(name="divorce", description="Гэрлэлтийг цуцлах")
    @app_commands.describe(user="Цуцлах хэрэглэгч (хоосон орхивол бүгдийг)")
    async def slash_divorce(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await self._divorce(interaction, user, is_slash=True)

    @marriage_group.command(name="adopt", description="Хүүхэд өргөмжлөх")
    @app_commands.describe(child="Хүүхдээр сонгох хэрэглэгч")
    async def slash_adopt(self, interaction: discord.Interaction, child: discord.Member):
        await self._adopt(interaction, child, is_slash=True)

    @marriage_group.command(name="makeparent", description="Эцэг эх болох санал тавих")
    @app_commands.describe(parent="Эцэг эхээр сонгох хэрэглэгч")
    async def slash_makeparent(self, interaction: discord.Interaction, parent: discord.Member):
        await self._makeparent(interaction, parent, is_slash=True)

    @marriage_group.command(name="runaway", description="Эцэг эхээсээ зугтах")
    async def slash_runaway(self, interaction: discord.Interaction):
        await self._runaway(interaction, is_slash=True)

    @marriage_group.command(name="partners", description="Хамтрагч(ид)-аа харах")
    async def slash_partners(self, interaction: discord.Interaction):
        await self._spouse(interaction, is_slash=True)

    @marriage_group.command(name="parent", description="Эцэг эхээ харах")
    async def slash_parent(self, interaction: discord.Interaction):
        await self._parent(interaction, is_slash=True)

    @marriage_group.command(name="children", description="Хүүхдүүдээ харах")
    async def slash_children(self, interaction: discord.Interaction):
        await self._children(interaction, is_slash=True)

    @marriage_group.command(name="tree", description="Гэр бүлийн мод (зураг)")
    @app_commands.describe(member="Хэнийх (хоосон орхивол өөрийн)")
    async def slash_tree(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await self._family_tree(interaction, member, is_slash=True)

    @marriage_group.command(name="fulltree", description="Бүрэн гэр бүлийн мод (хамтрагчийн гэр бүлийг оролцуулан)")
    @app_commands.describe(member="Хэнийх (хоосон орхивол өөрийн)")
    async def slash_fulltree(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        await self._family_tree(interaction, member, full=True, is_slash=True)

    @marriage_group.command(name="relationship", description="Хоёр хэрэглэгчийн хоорондын харилцаа")
    @app_commands.describe(user1="Эхний хэрэглэгч", user2="Хоёр дахь хэрэглэгч")
    async def slash_relationship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        await self._relationship(interaction, user1, user2, is_slash=True)

    @marriage_group.command(name="familysize", description="Гэр бүлийн гишүүдийн тоо")
    async def slash_familysize(self, interaction: discord.Interaction):
        await self._familysize(interaction, is_slash=True)

    # ═════════ HYBRID COMMANDS ═════════
    @commands.hybrid_command(name='propose')
    @app_commands.describe(user="Гэрлэх санал тавих хэрэглэгч")
    async def propose(self, ctx, user: discord.Member):
        await self._propose(ctx, user)

    @commands.hybrid_command(name='divorce')
    @app_commands.describe(user="Цуцлах хэрэглэгч (хоосон бол бүх гэрлэлтийг цуцална)")
    async def divorce(self, ctx, user: discord.Member = None):
        await self._divorce(ctx, user)

    @commands.hybrid_command(name='adopt')
    @app_commands.describe(child="Хүүхэд")
    async def adopt(self, ctx, child: discord.Member):
        await self._adopt(ctx, child)

    @commands.hybrid_command(name='disown')
    @app_commands.describe(child="Хүүхэд")
    async def disown(self, ctx, child: discord.Member):
        await self._disown(ctx, child)

    @commands.hybrid_command(name='spouse')
    async def spouse(self, ctx):
        await self._spouse(ctx)

    @commands.hybrid_command(name='love')
    async def love(self, ctx, target: discord.Member):
        await self._love(ctx, target)

    @commands.hybrid_command(name='gift')
    @app_commands.choices(gift_type=[app_commands.Choice(name=v["name"], value=k) for k, v in GIFTS.items()])
    async def gift(self, ctx, gift_type: str):
        await self._gift(ctx, gift_type)

    @commands.hybrid_command(name='familytree')
    async def family_tree(self, ctx, member: Optional[discord.Member] = None):
        await self._family_tree(ctx, member)

    @commands.hybrid_command(name='marriagepro')
    async def marriage_card(self, ctx, member: Optional[discord.Member] = None):
        await self._marriage_card(ctx, member)

    @app_commands.command(name="autoaccept", description="Гэрлэх саналыг автоматаар хүлээн авах")
    async def autoaccept(self, interaction: discord.Interaction, enabled: bool):
        await self.set_auto_accept(interaction.guild.id, interaction.user.id, enabled)
        await interaction.response.send_message(f"✅ Автомат хүлээн авалт: **{'ИДЭВХТЭЙ' if enabled else 'ИДЭВХГҮЙ'}**", ephemeral=True)

    @app_commands.command(name="marriage_setup", description="Гэрлэлтийн тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def marriage_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_guild_config(interaction.guild_id)
        view = MarriageSetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ═════════ БҮХ ҮЙЛДЛИЙН ТӨВ ФУНКЦУУД ═════════
    async def _propose(self, ctx_or_inter, user, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if user.bot or user.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Өөртөө эсвэл ботод санал тавьж болохгүй.", is_slash)
        cfg = await self.get_guild_config(guild.id)
        if not cfg["enabled"]:
            return await self._reply(ctx_or_inter, "❌ Гэрлэлтийн систем идэвхгүй.", is_slash)
        if await self.marriage_exists(guild.id, author.id, user.id):
            return await self._reply(ctx_or_inter, "❌ Та аль хэдийн энэ хүнтэй гэрлэсэн.", is_slash)
        spouses = await self.get_spouses(guild.id, author.id)
        if not cfg["polygamy"] and len(spouses) >= 1:
            return await self._reply(ctx_or_inter, "❌ Полигами зөвшөөрөгдөөгүй.", is_slash)
        if len(spouses) >= cfg["max_spouses"]:
            return await self._reply(ctx_or_inter, f"❌ Хамгийн ихдээ {cfg['max_spouses']} хүнтэй гэрлэх боломжтой.", is_slash)
        if await self.is_blocked(guild.id, user.id):
            return await self._reply(ctx_or_inter, f"🚫 {user.mention} гэрлэх санал авахаас татгалзсан.", is_slash)
        shop = self.bot.get_cog("ShopCog")
        ring_item_id, ring_name, ring_emoji = None, None, None
        if shop:
            inv = await shop.get_user_inventory(author.id, guild.id)
            for item_id, qty in inv.items():
                if await self._is_ring_item(item_id):
                    item = await shop.get_item(item_id)
                    if item:
                        ring_item_id, ring_name, ring_emoji = item_id, item.get("name", "Энгийн бөгж"), item.get("emoji", "💍")
                        break
            if not ring_item_id:
                return await self._reply(ctx_or_inter, "❌ Инвентарт гэрлэх бөгж байхгүй.", is_slash)
        else:
            return await self._reply(ctx_or_inter, "❌ Дэлгүүрийн систем ачаалагдаагүй.", is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(user.id),
             "proposal_type": "marriage", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="💍 ГЭРЛЭХ САНАЛ",
                              description=f"{author.mention} {user.mention}-д гэрлэх санал тавьж байна!\n\n💍 Бөгж: {ring_emoji} **{ring_name}**\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=GOLD_COLOR)
        view = ProposalView(self, guild.id, author.id, user.id, ring_name, ring_emoji, ring_item_id)
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=user.mention, embed=embed, view=view)

    async def _divorce(self, ctx_or_inter, user, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if user is None:
            marriages = await self.get_marriages(guild.id, author.id)
            if not marriages:
                return await self._reply(ctx_or_inter, "❌ Танд гэрлэлт байхгүй.", is_slash)
            for m in marriages:
                partner = guild.get_member(m["partner"])
                await self.remove_marriage(guild.id, author.id, m["partner"])
                await self.remove_marriage_role(guild, author)
                if partner: await self.remove_marriage_role(guild, partner)
            return await self._reply(ctx_or_inter, "💔 Бүх гэрлэлтийг цуцаллаа.", is_slash)
        else:
            if not await self.marriage_exists(guild.id, author.id, user.id):
                return await self._reply(ctx_or_inter, f"❌ Та {user.mention}-тэй гэрлээгүй байна.", is_slash)
            await self.remove_marriage(guild.id, author.id, user.id)
            await self.remove_marriage_role(guild, author)
            await self.remove_marriage_role(guild, user)
            await self.announce_divorce(guild, author, user)
            return await self._reply(ctx_or_inter, f"💔 {author.mention} болон {user.mention} саллаа.", is_slash)

    async def _adopt(self, ctx_or_inter, child, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if child.bot or child.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Бот эсвэл өөрийгөө өргөмжлөх боломжгүй.", is_slash)
        if await self.is_parent_child(guild.id, author.id, child.id):
            return await self._reply(ctx_or_inter, f"❌ {child.mention} аль хэдийн таны хүүхэд.", is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(child.id),
             "proposal_type": "adoption", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="👶 ХҮҮХЭД ӨРГӨМЖЛӨХ САНАЛ",
                              description=f"{author.mention} {child.mention}-г хүүхэд болгон өргөмжлөх санал тавьж байна!\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=PURPLE_COLOR)
        view = AdoptView(self.bot, guild.id, author.id, child.id, "adoption")
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=child.mention, embed=embed, view=view)

    async def _disown(self, ctx_or_inter, child, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if not await self.is_parent_child(guild.id, author.id, child.id):
            return await self._reply(ctx_or_inter, f"❌ {child.mention} таны хүүхэд биш.", is_slash)
        await self.remove_parent_child(guild.id, author.id, child.id)
        return await self._reply(ctx_or_inter, f"💔 {author.mention} {child.mention} -аас татгалзлаа.", is_slash)

    async def _makeparent(self, ctx_or_inter, parent, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if parent.bot or parent.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Бот эсвэл өөрийгөө эцэг эх болгох боломжгүй.", is_slash)
        if await self.is_parent_child(guild.id, parent.id, author.id):
            return await self._reply(ctx_or_inter, f"❌ {parent.mention} аль хэдийн таны эцэг эх.", is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(parent.id),
             "proposal_type": "parenthood", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="👪 ЭЦЭГ ЭХ БОЛОХ САНАЛ",
                              description=f"{author.mention} {parent.mention}-г эцэг эхээр сонгохыг хүсч байна!\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=PURPLE_COLOR)
        view = AdoptView(self.bot, guild.id, parent.id, author.id, "parenthood")
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=parent.mention, embed=embed, view=view)

    async def _runaway(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        parents = await self.get_parents(guild.id, author.id)
        if not parents:
            return await self._reply(ctx_or_inter, "❌ Танд эцэг эх байхгүй.", is_slash)
        for parent_id in parents:
            await self.remove_parent_child(guild.id, parent_id, author.id)
        return await self._reply(ctx_or_inter, "🏃 Зугтлаа! Эцэг эхийн харилцаа цуцлагдлаа.", is_slash)

    async def _spouse(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        spouses = await self.get_spouses(guild.id, author.id)
        if not spouses:
            return await self._reply(ctx_or_inter, "❌ Та гэрлээгүй байна.", is_slash)
        partners = [guild.get_member(sid).mention if guild.get_member(sid) else f"<@{sid}>" for sid in spouses]
        # ЗАСВАР: embed аргументын дараа is_slash-г нэртэй дамжуулах
        await self._reply(ctx_or_inter, embed=discord.Embed(title="💑 ХАМТРАГЧ(ИД)", description=", ".join(partners), color=LOVE_COLOR), is_slash=is_slash)

    async def _parent(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        parents = await self.get_parents(guild.id, author.id)
        if not parents:
            return await self._reply(ctx_or_inter, "❌ Танд эцэг эх байхгүй.", is_slash)
        parts = [guild.get_member(pid).mention if guild.get_member(pid) else f"<@{pid}>" for pid in parents]
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=discord.Embed(title="👪 ЭЦЭГ ЭХ", description=", ".join(parts), color=INFO_COLOR), is_slash=is_slash)

    async def _children(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        children = await self.get_children(guild.id, author.id)
        if not children:
            return await self._reply(ctx_or_inter, "❌ Танд хүүхэд байхгүй.", is_slash)
        parts = [guild.get_member(cid).mention if guild.get_member(cid) else f"<@{cid}>" for cid in children]
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=discord.Embed(title="👶 ХҮҮХДҮҮД", description=", ".join(parts), color=INFO_COLOR), is_slash=is_slash)

    async def _love(self, ctx_or_inter, target, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if not await self.marriage_exists(guild.id, author.id, target.id):
            return await self._reply(ctx_or_inter, f"❌ {target.mention} -тай гэрлээгүй байна.", is_slash)
        last = await self.get_last_love_time(guild.id, author.id)
        if last and int(time.time()) - last < 86400:
            remaining = int(86400 - (time.time() - last))
            hours, minutes = divmod(remaining // 60, 60)
            return await self._reply(ctx_or_inter, f"⏰ Өдөрт 1 удаа love бэлэглэх боломжтой. Үлдсэн: {hours}ц {minutes}м", is_slash)
        marriage = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild.id), "user_id": str(author.id), "partner_id": str(target.id)}
        )
        if not marriage:
            marriage = await self.bot.db_manager.fetch_one(
                "marriages", {"guild_id": str(guild.id), "user_id": str(target.id), "partner_id": str(author.id)}
            )
        if marriage:
            await self.bot.db_manager.update(
                "marriages",
                {"guild_id": str(guild.id), "user_id": str(author.id), "partner_id": str(target.id)},
                {"love_points": (marriage.get("love_points", 0) or 0) + 10},
            )
        await self.update_last_love_time(guild.id, author.id)
        await self._reply(ctx_or_inter, f"💖 {author.mention} {target.mention} -д 10 love оноо бэлэглэлээ!", is_slash)

    async def _gift(self, ctx_or_inter, gift_type, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        gift = GIFTS.get(gift_type)
        if not gift:
            return await self._reply(ctx_or_inter, "❌ Бэлэг олдсонгүй.", is_slash)
        spouses = await self.get_spouses(guild.id, author.id)
        if not spouses:
            return await self._reply(ctx_or_inter, "❌ Танд хань байхгүй.", is_slash)
        last = await self.get_last_gift_time(guild.id, author.id)
        if last and int(time.time()) - last < 86400:
            return await self._reply(ctx_or_inter, "❌ Өнөөдөр аль хэдийн бэлэг өгсөн. 24 цаг хүлээнэ үү.", is_slash)
        partner_id = spouses[0]
        await self.add_gift(guild.id, author.id, partner_id, gift_type, gift["love"])
        await self.update_last_gift_time(guild.id, author.id)
        await self._reply(ctx_or_inter, f"🎁 {author.mention} ханьдаа {gift['emoji']} **{gift['name']}** бэлэглэж, +{gift['love']}❤️ хайрын оноо нэмлээ!", is_slash)

    async def _family_tree(self, ctx_or_inter, member=None, full=False, is_slash=False):
        if is_slash:
            target = member or ctx_or_inter.user
            guild = ctx_or_inter.guild
            await ctx_or_inter.response.defer()
        else:
            target = member or ctx_or_inter.author
            guild = ctx_or_inter.guild
            await ctx_or_inter.defer() if hasattr(ctx_or_inter, 'defer') else None

        spouses_ids = await self.get_spouses(guild.id, target.id)
        children_ids = await self.get_children(guild.id, target.id)
        parents_ids = await self.get_parents(guild.id, target.id)

        async with aiohttp.ClientSession() as sess:
            main_url = target.display_avatar.replace(size=256, format="png").url
            ava_main = await self._download_avatar(sess, main_url, 160)

            async def fetch_ava_list(members):
                avas = []
                for mem, uid in members[:8]:
                    url = mem.display_avatar.replace(size=256, format="png").url if mem else None
                    if url:
                        ava = await self._download_avatar(sess, url, 80)
                        name = mem.display_name if mem else f"<@{uid}>"
                        avas.append((ava, name))
                return avas

            spouse_avas = await fetch_ava_list([(guild.get_member(sid), sid) for sid in spouses_ids])
            child_avas = await fetch_ava_list([(guild.get_member(cid), cid) for cid in children_ids])
            parent_avas = await fetch_ava_list([(guild.get_member(pid), pid) for pid in parents_ids])

        buf = await asyncio.to_thread(
            self._render_family_card, target, spouses_ids, children_ids, parents_ids,
            ava_main, spouse_avas[:4], child_avas[:4], parent_avas[:4]
        )
        embed = discord.Embed(color=SUCCESS_COLOR)
        embed.set_image(url="attachment://family_tree.png")
        embed.set_footer(text=f"{guild.name} • Гэр бүлийн мод")
        file = discord.File(buf, filename="family_tree.png")
        if is_slash:
            await ctx_or_inter.edit_original_response(embed=embed, attachments=[file])
        else:
            await ctx_or_inter.send(embed=embed, file=file)

    async def _marriage_card(self, ctx_or_inter, member=None, is_slash=False):
        if is_slash:
            target = member or ctx_or_inter.user
            guild = ctx_or_inter.guild
            await ctx_or_inter.response.defer()
        else:
            target = member or ctx_or_inter.author
            guild = ctx_or_inter.guild
            await ctx_or_inter.defer() if hasattr(ctx_or_inter, 'defer') else None
        buf = await self._build_marriage_card(target, guild)
        if buf is None:
            embed = discord.Embed(title="💔 Гэрлээгүй", description="Энэ хэрэглэгч гэрлээгүй байна.", color=ERROR_COLOR)
            if is_slash:
                await ctx_or_inter.edit_original_response(embed=embed)
            else:
                await ctx_or_inter.send(embed=embed)
            return
        embed = discord.Embed(color=LOVE_COLOR)
        embed.set_image(url="attachment://marriage_card.png")
        file = discord.File(buf, filename="marriage_card.png")
        if is_slash:
            await ctx_or_inter.edit_original_response(embed=embed, attachments=[file])
        else:
            await ctx_or_inter.send(embed=embed, file=file)

    async def _relationship(self, ctx_or_inter, user1, user2, is_slash=False):
        guild = ctx_or_inter.guild
        if await self.marriage_exists(guild.id, user1.id, user2.id):
            rel = "💑 Хань"
        elif await self.is_parent_child(guild.id, user1.id, user2.id):
            rel = "👪 Эцэг эх (та түүний эцэг эх)"
        elif await self.is_parent_child(guild.id, user2.id, user1.id):
            rel = "👶 Хүүхэд (тэр таны эцэг эх)"
        else:
            rel = "❓ Харилцаагүй"
        embed = discord.Embed(title="🔗 ХАРИЛЦАА", description=f"**{user1.display_name}** ↔ **{user2.display_name}**\n{rel}", color=INFO_COLOR)
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=embed, is_slash=is_slash)

    async def _familysize(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        spouses = len(await self.get_spouses(guild.id, author.id))
        children = len(await self.get_children(guild.id, author.id))
        parents = len(await self.get_parents(guild.id, author.id))
        total = spouses + children + parents + 1
        embed = discord.Embed(title="👨‍👩‍👧‍👦 ГЭР БҮЛИЙН ХЭМЖЭЭ",
                              description=f"**{author.display_name}**-ын гэр бүл:\n"
                                          f"💑 Хань: {spouses}\n"
                                          f"👶 Хүүхэд: {children}\n"
                                          f"👪 Эцэг эх: {parents}\n"
                                          f"✨ Нийт: {total}",
                              color=INFO_COLOR)
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=embed, is_slash=is_slash)

    async def _reply(self, ctx_or_inter, content=None, embed=None, is_slash=False):
        if is_slash:
            if not ctx_or_inter.response.is_done():
                await ctx_or_inter.response.send_message(content=content, embed=embed, ephemeral=True)
            else:
                await ctx_or_inter.followup.send(content=content, embed=embed, ephemeral=True)
        else:
            if content:
                await ctx_or_inter.send(content=content, embed=embed)
            else:
                await ctx_or_inter.send(embed=embed)

    async def _is_ring_item(self, item_id):
        shop = self.bot.get_cog("ShopCog")
        if not shop: return False
        item = await shop.get_item(item_id)
        return item is not None and item.get("category") == "ring"

    async def _build_marriage_card(self, member, guild):
        marriages = await self.get_marriages(guild.id, member.id)
        if not marriages: return None
        partner_id = marriages[0]["partner"]
        partner = guild.get_member(partner_id)
        love = marriages[0]["love_points"]
        ring = marriages[0]["ring"]
        raw_date = marriages[0]["marriage_date"]
        anniv = await self.get_anniversary(int(raw_date) if raw_date else None)
        async with aiohttp.ClientSession() as sess:
            url1 = member.display_avatar.replace(size=256, format="png").url
            url2 = partner.display_avatar.replace(size=256, format="png").url if partner else None
            ava1 = await self._download_avatar(sess, url1, 180)
            ava2 = await self._download_avatar(sess, url2, 180) if url2 else None
        return await asyncio.to_thread(self._render_marriage_card, member, partner, love, ring, anniv, ava1, ava2)

    # ═════════ ЗУРГИЙН ФУНКЦУУД ═════════
    def _render_family_card(self, member, spouses_ids, children_ids, parents_ids, ava_main, spouse_avas, child_avas, parent_avas):
        W, H = 1100, 650
        img = Image.new("RGBA", (W, H), (30, 30, 30, 255))
        draw = ImageDraw.Draw(img)
        font_main = _load_font(32, True)
        font_small = _load_font(18, False)
        main_size = 130
        main_x = W//2 - main_size//2
        main_y = 140
        img.paste(ava_main, (main_x, main_y), ava_main)
        draw.text((W//2, main_y + main_size + 15), member.display_name[:18], font=font_main, fill=(255,255,255), anchor="mt")
        def draw_avatar(ava, name, x, y, size=70):
            img.paste(ava, (x, y), ava)
            draw.text((x + size//2, y + size + 5), name[:10], font=font_small, fill=(200,200,200), anchor="mt")
        if spouse_avas:
            for i, (ava, name) in enumerate(spouse_avas[:2]):
                sx = W//2 - 220 if i == 0 else W//2 + 120
                draw_avatar(ava, name, sx, main_y + 30, 70)
        if child_avas:
            child_y = H - 160
            for i, (ava, name) in enumerate(child_avas[:5]):
                cx = 80 + i * 180
                draw_avatar(ava, name, cx, child_y, 65)
        if parent_avas:
            for i, (ava, name) in enumerate(parent_avas[:2]):
                px = W//2 - 160 if i == 0 else W//2 + 60
                draw_avatar(ava, name, px, 30, 70)
        draw.text((W//2, H-30), "🌳", font=font_main, fill=(255,255,255), anchor="mm")
        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); buf.seek(0)
        return buf

    def _render_marriage_card(self, member, partner, love, ring, anniv, ava1, ava2):
        W, H = 1200, 500
        img = Image.new("RGBA", (W, H), (25, 27, 35, 255))
        draw = ImageDraw.Draw(img)
        font_title = _load_font(60, True); font_sub = _load_font(42, True); font_info = _load_font(32, False)
        ava_size = 180
        left_x, right_x, center_y = 120, W - 120 - ava_size, 190
        img.paste(ava1, (left_x, center_y - ava_size//2), ava1)
        if ava2: img.paste(ava2, (right_x, center_y - ava_size//2), ava2)
        draw.text((left_x + ava_size//2, center_y + ava_size//2 + 35), member.display_name[:18], font=font_sub, fill=(255,255,255), anchor="mt")
        if partner: draw.text((right_x + ava_size//2, center_y + ava_size//2 + 35), partner.display_name[:18], font=font_sub, fill=(255,255,255), anchor="mt")
        draw.text((W//2, center_y - 60), "❤️", font=font_title, fill=(255,105,180), anchor="mm")
        love_level = max(1, love // 100 + 1)
        draw.text((W//2, center_y + 70), f"⚡ Lv. {love_level} Love", font=font_title, fill=(255,215,0), anchor="mm")
        days_text = f"✨ {anniv['days']} хоног хамт" if anniv else "✨ Дөнгөж гэрлэсэн"
        draw.text((W//2, center_y + 120), days_text, font=font_info, fill=(255,255,255), anchor="mm")
        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); buf.seek(0)
        return buf


async def setup(bot):
    await bot.add_cog(Marriage(bot))