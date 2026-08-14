import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
import asyncio
import time
import random

# ========== Модалууд (өмнөхтэй адил) ==========
class RenameModal(ui.Modal, title="Сувгийн нэрийг өөрчлөх"):
    name = ui.TextInput(label="Шинэ нэр", placeholder="Шинэ нэрээ бичнэ үү...", max_length=100)

    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)
        await channel.edit(name=self.name.value)
        await interaction.response.send_message(f"✅ Нэр **{self.name.value}** боллоо.", ephemeral=True)


class LimitModal(ui.Modal, title="Оролтын хязгаар тогтоох"):
    limit = ui.TextInput(label="Хязгаар (0-99)", placeholder="0 - хязгааргүй", default="0")

    def __init__(self, channel_id: int):
        super().__init__()
        self.channel_id = channel_id

    async def on_submit(self, interaction: discord.Interaction):
        try:
            limit = int(self.limit.value)
            if 0 <= limit <= 99:
                channel = interaction.guild.get_channel(self.channel_id)
                if not channel:
                    return await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)
                await channel.edit(user_limit=limit)
                text = "Хязгааргүй" if limit == 0 else f"{limit} хэрэглэгч"
                await interaction.response.send_message(f"✅ Хязгаар: {text}", ephemeral=True)
            else:
                await interaction.response.send_message("❌ 0-99 хооронд тоо оруулна уу.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Буруу формат.", ephemeral=True)


class MaxChannelsModal(ui.Modal, title="Хамгийн их түр суваг (тоо)"):
    max_channels = ui.TextInput(label="Хамгийн их сувгийн тоо", placeholder="3", default="3")

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            max_ch = int(self.max_channels.value)
            if max_ch < 1:
                return await interaction.response.send_message("❌ Хамгийн багадаа 1 байх ёстой.", ephemeral=True)
            await self.view.cog.set_config(interaction.guild_id, max_channels_per_user=max_ch)
            await interaction.response.send_message(f"✅ Хамгийн их түр суваг: {max_ch}", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)


# ========== Хэрэглэгч хөөх View ==========
class KickUserSelect(ui.View):
    def __init__(self, channel: discord.VoiceChannel, owner_id: int):
        super().__init__(timeout=60)
        self.channel = channel
        self.owner_id = owner_id

        members = [m for m in channel.members if not m.bot and m.id != owner_id]
        if not members:
            self.add_item(ui.Button(label="Хэрэглэгч байхгүй", disabled=True, style=ButtonStyle.gray))
            return

        options = [
            discord.SelectOption(label=m.display_name, value=str(m.id), description=f"ID: {m.id}")
            for m in members[:25]
        ]
        select = ui.Select(placeholder="Хөөх хэрэглэгчээ сонгоно уу...", options=options, min_values=1, max_values=1)

        async def kick_callback(interaction: discord.Interaction):
            if interaction.user.id != self.owner_id:
                return await interaction.response.send_message("❌ Та эзэмшигч биш!", ephemeral=True)
            user_id = int(select.values[0])
            member = interaction.guild.get_member(user_id)
            if not member or member not in self.channel.members:
                return await interaction.response.send_message("❌ Хэрэглэгч олдсонгүй.", ephemeral=True)
            try:
                await member.move_to(None)
                await interaction.response.send_message(f"✅ {member.mention} хөөгдлөө.", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ Хөөх эрх хүрэлцэхгүй.", ephemeral=True)
            self.stop()
            try:
                await interaction.message.delete()
            except:
                pass

        select.callback = kick_callback
        self.add_item(select)


# ========== УДИРДЛАГЫН VIEW (persistent) ==========
class ControlView(ui.View):
    def __init__(self, bot, channel_id: int, owner_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.channel_id = channel_id
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Та энэ сувгийн эзэн биш!", ephemeral=True)
            return False
        return True

    @ui.button(label="Түгжих", style=ButtonStyle.red, emoji="🔒", row=0)
    async def lock(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.set_permissions(interaction.guild.default_role, connect=False)
            await interaction.response.send_message("🔒 Суваг түгжигдлээ.", ephemeral=True)

    @ui.button(label="Тайлах", style=ButtonStyle.green, emoji="🔓", row=0)
    async def unlock(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            await channel.set_permissions(interaction.guild.default_role, connect=True)
            await interaction.response.send_message("🔓 Суваг нээлттэй.", ephemeral=True)

    @ui.button(label="Нэр өөрчлөх", style=ButtonStyle.blurple, emoji="✏️", row=1)
    async def rename(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(RenameModal(self.channel_id))

    @ui.button(label="Хязгаар", style=ButtonStyle.gray, emoji="👥", row=1)
    async def set_limit(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(LimitModal(self.channel_id))

    @ui.button(label="Хэрэглэгч хөөх", style=ButtonStyle.red, emoji="👢", row=2)
    async def kick_user(self, interaction: discord.Interaction, button: ui.Button):
        channel = interaction.guild.get_channel(self.channel_id)
        if not channel:
            return await interaction.response.send_message("❌ Суваг олдсонгүй.", ephemeral=True)
        view = KickUserSelect(channel, self.owner_id)
        await interaction.response.send_message("👤 **Хөөх хэрэглэгчээ сонгоно уу:**", view=view, ephemeral=True)


# ========== ТОХИРГООНЫ САМБАР (admin, persistent) ==========
class TempVoiceSetupView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=None)
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
        config = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(config, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, config, guild):
        embed = discord.Embed(title="🔊 Түр дуут сувгийн тохиргоо", color=discord.Color.blue())
        create_ch = guild.get_channel(config["create_channel_id"]) if config["create_channel_id"] else None
        cat = guild.get_channel(config["category_id"]) if config["category_id"] else None
        ctrl_ch = guild.get_channel(config["control_channel_id"]) if config["control_channel_id"] else None

        embed.add_field(name="🔹 Create суваг", value=create_ch.mention if create_ch else "❌ Тохируулаагүй", inline=False)
        embed.add_field(name="📁 Категори", value=cat.name if cat else "Create-н категори", inline=True)
        embed.add_field(name="👥 Хамгийн их суваг", value=f"{config['max_channels_per_user']}", inline=True)
        embed.add_field(name="📨 Удирдлагын суваг", value=ctrl_ch.mention if ctrl_ch else "DM", inline=True)
        embed.set_footer(text="Доорх сонголтуудаар тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.voice], placeholder="🔹 Create суваг сонго...", row=0)
    async def select_create_channel(self, interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.set_config(self.guild_id, create_channel_id=channel.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.category], placeholder="📁 Категори (хоосон орхивол create-н категори)", row=1)
    async def select_category(self, interaction, select: ui.ChannelSelect):
        category = select.values[0]
        await self.cog.set_config(self.guild_id, category_id=category.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📨 Удирдлагын суваг (заавал биш)", row=2)
    async def select_control_channel(self, interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.set_config(self.guild_id, control_channel_id=channel.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="📥 Суурилуулах", style=discord.ButtonStyle.green, row=3)
    async def install_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.cog.install_tempvoice(interaction.guild)
        config = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(config, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    @ui.button(label="👥 Хамгийн их суваг тохируулах", style=discord.ButtonStyle.secondary, row=4)
    async def max_channels_button(self, interaction, button):
        await interaction.response.send_modal(MaxChannelsModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=4)
    async def refresh_button(self, interaction, button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        pass  # persistent


# ========== ҮНДСЭН КОГ ==========
class TempVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.connect_times = {}

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        # Schedule view reloading as a background task to avoid blocking setup_hook
        self.bot.loop.create_task(self._reload_setup_views_after_ready())

    async def _reload_setup_views_after_ready(self):
        """Reload persistent views after the bot is ready (non-blocking)."""
        await self.bot.wait_until_ready()
        await self.reload_setup_views()

    async def reload_setup_views(self):
        rows = await self.bot.db_manager.fetch_safe("tempvoice_setup_msg", {})
        for row in rows:
            guild_id = row.get("guild_id")
            channel_id = row.get("channel_id")
            message_id = row.get("message_id")
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                continue
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            try:
                message = await channel.fetch_message(message_id)
            except:
                continue
            admin_id = guild.owner_id
            view = TempVoiceSetupView(self, guild.id, admin_id)
            await message.edit(view=view)
            view.message = message

    async def get_config(self, guild_id):
        row = await self.bot.db_manager.fetch_one("guild_config", {"guild_id": str(guild_id)})
        if not row:
            return {"create_channel_id": None, "category_id": None, "max_channels_per_user": 3, "control_channel_id": None}
        return {
            "create_channel_id": row.get("create_channel_id"),
            "category_id": row.get("category_id"),
            "max_channels_per_user": row.get("max_channels_per_user") or 3,
            "control_channel_id": row.get("control_channel_id")
        }

    async def set_config(self, guild_id, **kwargs):
        data = {"guild_id": str(guild_id)}
        data.update(kwargs)
        await self.bot.db_manager.upsert("guild_config", data, on_conflict="guild_id")

    async def install_tempvoice(self, guild: discord.Guild):
        config = await self.get_config(guild.id)
        for ch_id in [config["create_channel_id"], config["control_channel_id"]]:
            if ch_id:
                ch = guild.get_channel(ch_id)
                if ch:
                    try: await ch.delete(reason="TempVoice шинэ суурилуулалт")
                    except: pass
        old_cat_id = config["category_id"]
        if old_cat_id:
            cat = guild.get_channel(old_cat_id)
            if cat and len(cat.channels) == 0:
                try: await cat.delete(reason="TempVoice шинэ суурилуулалт")
                except: pass

        overwrites_cat = {guild.default_role: discord.PermissionOverwrite(view_channel=True)}
        category = await guild.create_category("🔊 Түр суваг", overwrites=overwrites_cat)
        vc = await guild.create_voice_channel("➕ Create", category=category)
        txt = await guild.create_text_channel("🎛️ удирдлага", category=category)
        await self.set_config(guild.id, create_channel_id=vc.id, category_id=category.id, control_channel_id=txt.id)

    async def send_control_panel(self, member: discord.Member, channel: discord.VoiceChannel):
        config = await self.get_config(member.guild.id)
        embed = discord.Embed(
            title="🎛️ Түр сувгийн удирдлага",
            description=f"**{channel.name}** сувгийг доорх товчлуураар удирдана уу.",
            color=discord.Color.green()
        )
        embed.add_field(name="Эзэмшигч", value=member.mention)
        embed.set_footer(text="Удирдлагын самбар байнгын идэвхтэй.")
        view = ControlView(self.bot, channel.id, member.id)

        target = None
        if config["control_channel_id"]:
            target = member.guild.get_channel(config["control_channel_id"])

        if target:
            try:
                await target.send(embed=embed, view=view)
                return
            except discord.Forbidden:
                pass

        try:
            await member.send(embed=embed, view=view)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return

        if after.channel and not before.channel:
            self.connect_times[member.id] = time.time()

        if before.channel and not after.channel:
            connect_time = self.connect_times.pop(member.id, None)
            if connect_time:
                elapsed = time.time() - connect_time
                minutes = int(elapsed // 60)
                if minutes > 0:
                    quests_cog = self.bot.get_cog("Quests")
                    if quests_cog:
                        await quests_cog.trigger_event(member.id, member.guild.id, "tempvoice_time", minutes)

        if after.channel and not before.channel:
            config = await self.get_config(member.guild.id)
            if not config["create_channel_id"] or after.channel.id != config["create_channel_id"]:
                return

            max_channels = config["max_channels_per_user"]
            cat_id = config["category_id"] or after.channel.category_id
            category = member.guild.get_channel(cat_id) if cat_id else after.channel.category

            temp_rows = await self.bot.db_manager.fetch_all(
                "temp_channels",
                {"guild_id": str(member.guild.id), "owner_id": str(member.id)},
            )
            count = len(temp_rows)
            if count >= max_channels:
                try: await member.send(f"❌ Хамгийн ихдээ {max_channels} түр суваг үүсгэх боломжтой.")
                except: pass
                await member.move_to(None)
                return

            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
                member: discord.PermissionOverwrite(manage_channels=True, mute_members=True, deafen_members=True)
            }
            try:
                new_channel = await member.guild.create_voice_channel(
                    name=f"🔊 {member.display_name}",
                    category=category,
                    overwrites=overwrites
                )
                await member.move_to(new_channel)
            except discord.Forbidden:
                return

            await self.bot.db_manager.insert("temp_channels", {
                "guild_id": str(member.guild.id),
                "channel_id": str(new_channel.id),
                "owner_id": str(member.id),
            })
            await self.send_control_panel(member, new_channel)

        if before.channel:
            channel = before.channel
            temp_row = await self.bot.db_manager.fetch_one(
                "temp_channels", {"channel_id": str(channel.id)}
            )
            if temp_row and len(channel.members) == 0:
                await asyncio.sleep(3)
                if len(channel.members) == 0:
                    try: await channel.delete(reason="Хоосон түр суваг")
                    except: pass
                    await self.bot.db_manager.delete(
                        "temp_channels", {"channel_id": str(channel.id)}
                    )

    # ==================== АДМИН ТОХИРГОО ====================
    @app_commands.command(name="voicesetup", description="Түр дуут сувгийн тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def voicesetup(self, interaction: discord.Interaction):
        """Санамсаргүй текст сувагт persistent самбар илгээнэ"""
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        # Санамсаргүй текст суваг сонгох
        text_channels = [ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages]
        if not text_channels:
            return await interaction.followup.send("❌ Серверт илгээх боломжтой текст суваг олдсонгүй.", ephemeral=True)

        random_channel = random.choice(text_channels)

        config = await self.get_config(guild.id)
        view = TempVoiceSetupView(self, guild.id, interaction.user.id)
        embed = view.build_embed(config, guild)

        try:
            message = await random_channel.send(embed=embed, view=view)
        except discord.Forbidden:
            return await interaction.followup.send(
                f"❌ {random_channel.mention} сувагт илгээх эрх байхгүй.", ephemeral=True
            )

        view.message = message

        # Хуучин persistent самбарыг шинэчлэх
        await self.bot.db_manager.upsert(
            "tempvoice_setup_msg",
            {"guild_id": str(guild.id), "channel_id": str(random_channel.id), "message_id": str(message.id)},
            on_conflict="guild_id",
        )

        await interaction.followup.send(
            f"✅ Тохиргооны самбар **{random_channel.mention}** сувагт илгээгдлээ.",
            ephemeral=True
        )

    @app_commands.command(name="voicesettings", description="Одоогийн түр сувгийн тохиргоог харах")
    async def voicesettings(self, interaction: discord.Interaction):
        config = await self.get_config(interaction.guild_id)
        create_ch = interaction.guild.get_channel(config["create_channel_id"]) if config["create_channel_id"] else None
        cat = interaction.guild.get_channel(config["category_id"]) if config["category_id"] else None
        ctrl_ch = interaction.guild.get_channel(config["control_channel_id"]) if config["control_channel_id"] else None
        embed = discord.Embed(title="🔊 Түр дуут сувгийн тохиргоо", color=discord.Color.blue())
        embed.add_field(name="Create суваг", value=create_ch.mention if create_ch else "❌ Тохируулаагүй", inline=False)
        embed.add_field(name="Категори", value=cat.name if cat else "Create-н категори", inline=False)
        embed.add_field(name="Хамгийн их суваг", value=f"{config['max_channels_per_user']}", inline=False)
        embed.add_field(name="Удирдлагын самбарын суваг", value=ctrl_ch.mention if ctrl_ch else "DM", inline=False)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(TempVoice(bot))