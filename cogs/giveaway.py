from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
import datetime
import random
import re
from typing import Optional

# ===== COLOR SCHEME =====
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

COLOR_MAP = {
    "gold": GOLD_COLOR,
    "blue": INFO_COLOR,
    "red": ERROR_COLOR,
    "green": SUCCESS_COLOR,
    "purple": 0xcba6f7,
    "dark": EMBED_COLOR,
    "grey": 0x6c7086,
}

# ==================== МОДАЛ: ТОХИРГОО ОРУУЛАХ ====================
class PrizeModal(ui.Modal, title="🎁 Шагнал оруулах"):
    prize = ui.TextInput(label="Шагналын нэр", placeholder="Жишээ: Discord Nitro 1 сар", required=True)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        self.view.prize = self.prize.value
        await interaction.response.send_message(f"✅ Шагнал: **{self.prize.value}**", ephemeral=True)
        await self.view.refresh(interaction)

class DurationModal(ui.Modal, title="⏱️ Хугацаа оруулах"):
    duration = ui.TextInput(label="Хугацаа (10s, 5m, 2h, 1d, 1w)", placeholder="1h", required=True)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        self.view.duration_str = self.duration.value
        await interaction.response.send_message(f"✅ Хугацаа: **{self.duration.value}**", ephemeral=True)
        await self.view.refresh(interaction)

class WinnersModal(ui.Modal, title="👑 Ялагчдын тоо"):
    winners = ui.TextInput(label="Ялагчдын тоо (тоо)", placeholder="1", required=True)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        try:
            w = int(self.winners.value)
            if w < 1:
                await interaction.response.send_message("❌ Ялагчдын тоо 1-ээс багагүй байх ёстой.", ephemeral=True)
                return
            self.view.winners = w
            await interaction.response.send_message(f"✅ Ялагчдын тоо: **{w}**", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

class RoleModal(ui.Modal, title="🔒 Шаардлагатай роль (ID)"):
    role_id = ui.TextInput(label="Ролийн Discord ID (хоосон орхивол шаардлагагүй)", placeholder="123456789", required=False)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        rid = self.role_id.value.strip()
        if rid:
            try:
                role = interaction.guild.get_role(int(rid))
                if not role:
                    return await interaction.response.send_message("❌ Роль олдсонгүй.", ephemeral=True)
                self.view.required_role = role
                await interaction.response.send_message(f"✅ Шаардлагатай роль: {role.mention}", ephemeral=True)
            except ValueError:
                return await interaction.response.send_message("❌ Буруу ID.", ephemeral=True)
        else:
            self.view.required_role = None
            await interaction.response.send_message("✅ Шаардлагатай рольгүй.", ephemeral=True)
        await self.view.refresh(interaction)

class ColorModal(ui.Modal, title="🎨 Embed өнгө сонгох"):
    color_choice = ui.TextInput(label="Өнгө (gold, blue, red, green, purple, dark, grey)", placeholder="gold", required=False)
    def __init__(self, view):
        super().__init__()
        self.view = view
    async def on_submit(self, interaction: discord.Interaction):
        color = self.color_choice.value.strip().lower()
        if color in COLOR_MAP:
            self.view.embed_color = COLOR_MAP[color]
            await interaction.response.send_message(f"✅ Өнгө: **{color}**", ephemeral=True)
        else:
            self.view.embed_color = GOLD_COLOR
            await interaction.response.send_message(f"⚠️ Тодорхойгүй өнгө, анхдагч алтанг ашиглалаа.", ephemeral=True)
        await self.view.refresh(interaction)

class GiveawayEnterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎉 Оролцох", style=discord.ButtonStyle.success, custom_id="giveaway_enter")
    async def enter_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        gw = await interaction.client.db_manager.fetch_one(
            "giveaways", {"message_id": str(interaction.message.id)}
        )

        if not gw:
            await interaction.response.send_message("❌ Энэ giveaway олдсонгүй.", ephemeral=True)
            return

        gid, prize, end_time, req_role_id, ended = (
            gw.get("id"), gw.get("prize"), gw.get("end_time"),
            gw.get("required_role_id"), gw.get("ended", 0)
        )

        if ended:
            await interaction.response.send_message("❌ Энэ giveaway аль хэдийн дууссан.", ephemeral=True)
            return

        if datetime.datetime.now(datetime.timezone.utc).timestamp() >= end_time:
            await interaction.response.send_message("❌ Энэ giveaway дууссан байна.", ephemeral=True)
            return

        if req_role_id:
            role = interaction.guild.get_role(req_role_id)
            if role and role not in interaction.user.roles:
                await interaction.response.send_message(f"❌ Танд {role.mention} роль байхгүй.", ephemeral=True)
                return

        existing = await interaction.client.db_manager.fetch_one(
            "giveaway_entries",
            {"giveaway_id": gid, "user_id": str(interaction.user.id)},
        )
        if existing:
            await interaction.response.send_message("⚠️ Та аль хэдийн оролцсон!", ephemeral=True)
            return

        await interaction.client.db_manager.insert("giveaway_entries", {
            "giveaway_id": gid,
            "user_id": str(interaction.user.id),
        })

        # Даалгаврын системд мэдэгдэх
        quests_cog = interaction.client.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(interaction.user.id, interaction.guild.id, "giveaway_enter", 1)

        await interaction.response.send_message("✅ Амжилттай оролцлоо! Амжилт хүсье 🎉", ephemeral=True)


# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class GiveawaySetupView(ui.View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=600)
        self.cog = cog
        self.ctx = ctx
        self.message = None

        # Тохиргооны утгууд
        self.channel: Optional[discord.TextChannel] = None
        self.prize: Optional[str] = None
        self.duration_str: Optional[str] = None
        self.winners: int = 1
        self.required_role: Optional[discord.Role] = None
        self.embed_color: int = GOLD_COLOR

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    def parse_duration(self, duration: str) -> int:
        match = re.match(r"(\d+)\s*([smhdw])", duration.lower())
        if not match:
            return None
        value = int(match.group(1))
        unit = match.group(2)
        multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        return value * multipliers.get(unit, 1)

    async def refresh(self, interaction: discord.Interaction):
        embed = self.build_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self):
        desc = "Доорх товчлууруудаар тохиргоог хийж, **Үүсгэх** товчоор giveaway-г эхлүүлнэ үү."
        channel_text = self.channel.mention if self.channel else "❌ Сонгогдоогүй"
        prize_text = self.prize or "❌ Оруулаагүй"
        duration_text = self.duration_str or "❌ Оруулаагүй"
        winners_text = f"{self.winners} хүн"
        role_text = self.required_role.mention if self.required_role else "Байхгүй"
        color_name = [k for k, v in COLOR_MAP.items() if v == self.embed_color][0] if self.embed_color in COLOR_MAP.values() else "unknown"

        embed = discord.Embed(
            title="🎁 GIVEAWAY ТОХИРГОО",
            description=desc,
            color=self.embed_color
        )
        embed.add_field(name="📢 Суваг", value=channel_text, inline=True)
        embed.add_field(name="🎁 Шагнал", value=prize_text, inline=True)
        embed.add_field(name="⏱️ Хугацаа", value=duration_text, inline=True)
        embed.add_field(name="👑 Ялагчид", value=winners_text, inline=True)
        embed.add_field(name="🔒 Шаардлагатай роль", value=role_text, inline=True)
        embed.add_field(name="🎨 Өнгө", value=color_name, inline=True)
        return embed

    # ---------- СУВАГ СОНГОХ ----------
    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Giveaway илгээх суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        self.channel = select.values[0]
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- ТОВЧЛУУД ----------
    @ui.button(label="🎁 Шагнал", style=discord.ButtonStyle.primary, row=1)
    async def prize_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(PrizeModal(self))

    @ui.button(label="⏱️ Хугацаа", style=discord.ButtonStyle.secondary, row=1)
    async def duration_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DurationModal(self))

    @ui.button(label="👑 Ялагчид", style=discord.ButtonStyle.secondary, row=1)
    async def winners_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(WinnersModal(self))

    @ui.button(label="🔒 Роль", style=discord.ButtonStyle.secondary, row=2)
    async def role_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RoleModal(self))

    @ui.button(label="🎨 Өнгө", style=discord.ButtonStyle.secondary, row=2)
    async def color_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ColorModal(self))

    @ui.button(label="✅ ҮҮСГЭХ", style=discord.ButtonStyle.success, row=3)
    async def create_button(self, interaction: discord.Interaction, button: ui.Button):
        # Валидац
        if not self.channel:
            await interaction.response.send_message("❌ Сувгаа сонгоно уу.", ephemeral=True)
            return
        if not self.prize:
            await interaction.response.send_message("❌ Шагналаа оруулна уу.", ephemeral=True)
            return
        if not self.duration_str:
            await interaction.response.send_message("❌ Хугацаагаа оруулна уу.", ephemeral=True)
            return

        seconds = self.parse_duration(self.duration_str)
        if seconds is None:
            await interaction.response.send_message("❌ Хугацааны формат буруу (жишээ: 1h, 30m).", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        # Giveaway үүсгэх
        end_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=seconds)
        end_timestamp = int(end_time.timestamp())

        embed = discord.Embed(
            title="🎉 **GIVEAWAY** 🎉",
            description=(
                f"**Шагнал:** {self.prize}\n"
                f"**Ялагчдын тоо:** {self.winners}\n"
                f"**Зохион байгуулагч:** {interaction.user.mention}\n"
                f"**Дуусах:** <t:{end_timestamp}:R>"
            ),
            color=self.embed_color
        )
        if self.required_role:
            embed.description += f"\n**Шаардлагатай роль:** {self.required_role.mention}"

        view = GiveawayEnterView()
        message = await self.channel.send(embed=embed, view=view)

        await self.ctx.bot.db_manager.insert("giveaways", {
            "guild_id": str(interaction.guild.id),
            "channel_id": str(self.channel.id),
            "message_id": str(message.id),
            "prize": self.prize,
            "winner_count": self.winners,
            "end_time": end_timestamp,
            "host_id": str(interaction.user.id),
            "required_role_id": str(self.required_role.id) if self.required_role else None,
        })

        await interaction.followup.send(f"✅ Giveaway {self.channel.mention}-д амжилттай үүслээ!", ephemeral=True)
        await self.refresh(interaction)  # самбарыг шинэчлэх

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            try:
                for child in self.children:
                    child.disabled = True
                await self.message.edit(view=self)
            except:
                pass


# ==================== ҮНДСЭН COG ====================
class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaway_check.start()

    def cog_unload(self):
        self.giveaway_check.cancel()

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        self.bot.add_view(GiveawayEnterView())

    async def get_entries(self, giveaway_id: int, required_role_id: int, guild: discord.Guild):
        rows = await self.bot.db_manager.fetch_all(
            "giveaway_entries", {"giveaway_id": giveaway_id}
        )
        entries = [r["user_id"] for r in rows]
        if required_role_id:
            role = guild.get_role(required_role_id)
            if role:
                entries = [uid for uid in entries if (member := guild.get_member(int(uid))) and role in member.roles]
        return entries

    async def finish_giveaway(self, message: discord.Message, giveaway_id: int, winners: list, prize: str, host: discord.Member):
        winner_mentions = " ".join(f"<@{uid}>" for uid in winners)
        embed = discord.Embed(
            title="🎉 **GIVEAWAY ДУУСЛАА** 🎉",
            description=f"**Шагнал:** {prize}\n**Ялагч(ид):** {winner_mentions}\n**Зохион байгуулагч:** {host.mention}",
            color=SUCCESS_COLOR
        )
        await message.edit(embed=embed, view=None)
        await message.channel.send(embed=embed)

        # Даалгаврын системд мэдэгдэх (ялагч бүрт)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            for uid in winners:
                await quests_cog.trigger_event(int(uid), message.guild.id, "giveaway_win", 1)

        await self.bot.db_manager.update(
            "giveaways", {"id": giveaway_id}, {"ended": 1}
        )

    async def _get_giveaway_by_message(self, message_id: int):
        gw = await self.bot.db_manager.fetch_one(
            "giveaways", {"message_id": str(message_id)}
        )
        if not gw:
            return None
        return (
            gw.get("id"), gw.get("channel_id"), gw.get("message_id"), gw.get("prize"),
            gw.get("winner_count"), gw.get("host_id"), gw.get("required_role_id"),
            gw.get("ended", 0), gw.get("end_time"), gw.get("guild_id")
        )

    # ==================== АДМИН КОМАНДУУД ====================
    giveaway_group = app_commands.Group(name="giveaway", description="Giveaway удирдлага")

    @giveaway_group.command(name="setup", description="Giveaway тохиргооны самбар нээх")
    @app_commands.default_permissions(manage_guild=True)
    async def giveaway_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = GiveawaySetupView(self, interaction)
        embed = view.build_embed()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @giveaway_group.command(name="end", description="Giveaway дуусгах")
    @app_commands.describe(message_id="Дуусгах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    async def end_giveaway(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer()
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if giveaway[7]:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway аль хэдийн дууссан.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Суваг олдсонгүй.", color=ERROR_COLOR))
        try:
            message = await channel.fetch_message(msg_id)
        except:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Мессеж олдсонгүй.", color=ERROR_COLOR))

        entries = await self.get_entries(gid, req_role_id, interaction.guild)
        if not entries:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Оролцогч байхгүй.", color=ERROR_COLOR))

        winners = random.sample(entries, min(winner_count, len(entries)))
        await self.finish_giveaway(message, gid, winners, prize, interaction.user)

    @giveaway_group.command(name="reroll", description="Giveaway дахин сонгох")
    @app_commands.describe(message_id="Дахин сонгох giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    async def reroll_giveaway(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer()
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if not giveaway[7]:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway дуусаагүй байна. Эхлээд дуусгах хэрэгтэй.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Суваг олдсонгүй.", color=ERROR_COLOR))
        try:
            await channel.fetch_message(msg_id)
        except:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Мессеж олдсонгүй.", color=ERROR_COLOR))

        entries = await self.get_entries(gid, req_role_id, interaction.guild)
        if not entries:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Дахин сонгох оролцогч байхгүй.", color=ERROR_COLOR))

        new_winners = random.sample(entries, min(winner_count, len(entries)))
        winner_mentions = " ".join(f"<@{uid}>" for uid in new_winners)
        embed = discord.Embed(
            title="🎉 **GIVEAWAY ДАХИН СОНГОГДЛОО** 🎉",
            description=f"**Шагнал:** {prize}\n**Шинэ ялагч(ид):** {winner_mentions}\n**Дахин сонгосон:** {interaction.user.mention}",
            color=GOLD_COLOR
        )
        await channel.send(embed=embed)

        # Даалгаврын системд мэдэгдэх (шинэ ялагчдад)
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            for uid in new_winners:
                await quests_cog.trigger_event(int(uid), interaction.guild.id, "giveaway_win", 1)

        await interaction.followup.send(f"✅ {message_id} giveaway-н ялагчид дахин сонгогдлоо.")

    @giveaway_group.command(name="cancel", description="Giveaway цуцлах")
    @app_commands.describe(message_id="Цуцлах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    async def cancel_giveaway(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer()
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR))
        if giveaway[7]:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway аль хэдийн дууссан эсвэл цуцлагдсан.", color=ERROR_COLOR))

        gid, channel_id, msg_id, prize, winner_count, host_id, req_role_id, ended, end_time, guild_id = giveaway

        channel = self.bot.get_channel(channel_id)
        if channel:
            try:
                message = await channel.fetch_message(msg_id)
                embed = discord.Embed(
                    title="❌ **GIVEAWAY ЦУЦЛАГДЛАА**",
                    description=f"**Шагнал:** {prize}\n**Зохион байгуулагч:** <@{host_id}>\n**Цуцалсан:** {interaction.user.mention}",
                    color=ERROR_COLOR
                )
                await message.edit(embed=embed, view=None)
            except:
                pass

        await self.bot.db_manager.update("giveaways", {"id": gid}, {"ended": 1})
        await interaction.followup.send(f"✅ Giveaway (ID: {message_id}) цуцлагдлаа.")

    @giveaway_group.command(name="entries", description="Оролцогчдын тоог харах")
    @app_commands.describe(message_id="Оролцогчдын тоог харах giveaway мессежийн ID")
    @app_commands.default_permissions(manage_guild=True)
    async def entries_giveaway(self, interaction: discord.Interaction, message_id: int):
        await interaction.response.defer(ephemeral=True)
        giveaway = await self._get_giveaway_by_message(message_id)
        if not giveaway:
            return await interaction.followup.send(embed=discord.Embed(title="❌ Giveaway олдсонгүй.", color=ERROR_COLOR), ephemeral=True)

        gid = giveaway[0]
        req_role_id = giveaway[6]
        entries = await self.get_entries(gid, req_role_id, interaction.guild)
        await interaction.followup.send(f"📊 **{len(entries)}** оролцогч байна.", ephemeral=True)

    @giveaway_group.command(name="list", description="Идэвхтэй giveaway-үүдийн жагсаалт")
    @app_commands.default_permissions(manage_guild=True)
    async def list_giveaways(self, interaction: discord.Interaction):
        await interaction.response.defer()
        rows = await self.bot.db_manager.fetch_all(
            "giveaways",
            {"guild_id": str(interaction.guild.id), "ended": 0},
        )
        rows = [
            (r["message_id"], r["prize"], r["end_time"], r["channel_id"])
            for r in rows
        ]
        if not rows:
            return await interaction.followup.send(embed=discord.Embed(title="📭 Идэвхтэй giveaway байхгүй", color=WARNING_COLOR))

        embed = discord.Embed(title="🎁 Идэвхтэй Giveaway-үүд", color=GOLD_COLOR)
        for msg_id, prize, end_time, ch_id in rows:
            channel = self.bot.get_channel(ch_id)
            ch_mention = channel.mention if channel else f"<#{ch_id}>"
            embed.add_field(
                name=f"ID: {msg_id}",
                value=f"**Шагнал:** {prize}\n**Дуусах:** <t:{end_time}:R>\n**Суваг:** {ch_mention}",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    # ==================== AUTO CHECK LOOP ====================
    @tasks.loop(minutes=1.0)
    async def giveaway_check(self):
        await self.bot.wait_until_ready()
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        giveaway_rows = await self.bot.db_manager.fetch_all("giveaways", {"ended": 0})
        expired = [
            r for r in giveaway_rows
            if (r.get("end_time") or 0) <= now
        ]

        for gw in expired:
            gid = gw.get("id")
            channel_id = gw.get("channel_id")
            msg_id = gw.get("message_id")
            prize = gw.get("prize")
            winner_count = gw.get("winner_count", 1)
            host_id = gw.get("host_id")
            req_role_id = gw.get("required_role_id")

            channel = self.bot.get_channel(channel_id)
            if not channel:
                await self.bot.db_manager.update("giveaways", {"id": gid}, {"ended": 1})
                continue
            try:
                message = await channel.fetch_message(msg_id)
            except:
                await self.bot.db_manager.update("giveaways", {"id": gid}, {"ended": 1})
                continue

            guild = channel.guild
            entries = await self.get_entries(gid, req_role_id, guild)
            if entries:
                winners = random.sample(entries, min(winner_count, len(entries)))
                host_user = guild.get_member(host_id) or await self.bot.fetch_user(host_id)
                await self.finish_giveaway(message, gid, winners, prize, host_user)
            else:
                embed = discord.Embed(
                    title="🎉 **GIVEAWAY ДУУСЛАА** 🎉",
                    description=f"**Шагнал:** {prize}\n**Оролцогч байхгүй.**",
                    color=ERROR_COLOR
                )
                await message.edit(embed=embed, view=None)
                await message.channel.send(embed=embed)
                await self.bot.db_manager.update("giveaways", {"id": gid}, {"ended": 1})

    @giveaway_check.before_loop
    async def before_giveaway_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Giveaway(bot))
