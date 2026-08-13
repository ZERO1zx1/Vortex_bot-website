from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime

# ===== COLOR SCHEME =====
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ==================== МОДАЛ: НУУЦ ЗАХИА ИЛГЭЭХ ====================
class ConfessionModal(ui.Modal, title="📩 Нууц захиа илгээх"):
    title_input = ui.TextInput(
        label="Захианы гарчиг (илэрхийлэл)",
        placeholder="Гарчиг оруулна уу...",
        max_length=100,
        required=True
    )
    content_input = ui.TextInput(
        label="Захианы агуулга",
        style=discord.TextStyle.paragraph,
        placeholder="Нууц захиагаа энд бичнэ үү...",
        max_length=1500,
        required=True
    )

    def __init__(self, cog, interaction: discord.Interaction):
        super().__init__()
        self.cog = cog
        self.ia = interaction

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.process_confession(
            user=interaction.user,
            guild=interaction.guild,
            content=f"**{self.title_input.value}**\n{self.content_input.value}",
            interaction=interaction
        )

# ==================== МОДАЛ: КҮҮДАУН ТОХИРУУЛАХ ====================
class CooldownModal(ui.Modal, title="⏱️ Күүдаун тохируулах"):
    seconds = ui.TextInput(
        label="Күүдаун (секундээр)",
        placeholder="Жишээ: 60",
        default="30",
        required=True
    )

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            cd = int(self.seconds.value)
            if cd < 0:
                await interaction.response.send_message("❌ Эерэг тоо оруулна уу.", ephemeral=True)
                return
            await self.view.cog.update_config(interaction.guild_id, cooldown=cd)
            await interaction.response.send_message(f"✅ Күүдаун {cd} секунд болж өөрчлөгдлөө.", ephemeral=True)
            await self.view.refresh(interaction)
        except ValueError:
            await interaction.response.send_message("❌ Зөвхөн тоо оруулна уу.", ephemeral=True)

# ==================== ТОХИРГООНЫ САМБАР (VIEW) ====================
class SetupView(ui.View):
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
        cfg = await self.cog.get_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed, view=self)

    def build_embed(self, cfg, guild):
        if cfg is None:
            desc = "⚠️ Тохиргоо хийгдээгүй байна. Сувгуудыг сонгон, тохиргоогоо хийгээрэй."
            channel1 = "❌ Сонгогдоогүй"
            channel2 = "❌ Сонгогдоогүй"
            anon = "?"
            cd = "?"
        else:
            ch1 = guild.get_channel(cfg['confess_channel'])
            ch2 = guild.get_channel(cfg['output_channel'])
            channel1 = ch1.mention if ch1 else "Устгагдсан"
            channel2 = ch2.mention if ch2 else "Устгагдсан"
            anon = "Идэвхтэй 🔒" if cfg['anonymity'] else "Унтарсан 🔓"
            cd = f"{cfg['cooldown']} сек"
            desc = ""

        embed = discord.Embed(
            title="🔧 Нууц захианы тохиргоо",
            description=desc,
            color=INFO_COLOR
        )
        embed.add_field(name="📥 Оролтын суваг", value=channel1, inline=True)
        embed.add_field(name="📤 Гаралтын суваг", value=channel2, inline=True)
        embed.add_field(name="🕶️ Аноним байдал", value=anon, inline=True)
        embed.add_field(name="⏱️ Күүдаун", value=cd, inline=True)
        embed.set_footer(text="Дээрх сонголтуудыг ашиглан тохиргоог өөрчилнө үү.")
        return embed

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📥 Нууц захианы суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_confess_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.update_config(self.guild_id, confess_channel_id=channel.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📤 Гаралтын суваг сонго...", min_values=1, max_values=1, row=1)
    async def select_output_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        channel = select.values[0]
        await self.cog.update_config(self.guild_id, output_channel_id=channel.id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="🕶️ Аноним төлөв солих", style=discord.ButtonStyle.primary, row=2)
    async def toggle_anon(self, interaction: discord.Interaction, button: ui.Button):
        cfg = await self.cog.get_config(self.guild_id)
        if cfg is None:
            await interaction.response.send_message("❌ Эхлээд сувгуудыг сонгоно уу.", ephemeral=True)
            return
        new_state = not cfg['anonymity']
        await self.cog.update_config(self.guild_id, anonymity=new_state)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="⏱️ Күүдаун тохируулах", style=discord.ButtonStyle.secondary, row=2)
    async def cooldown_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(CooldownModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=2)
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
class Confessions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----- DB туслахууд -----
    async def get_config(self, guild_id):
        row = await self.bot.db_manager.fetch_one("confession_config", {"guild_id": str(guild_id)})
        if not row:
            return None
        return {
            "confess_channel": row.get("confess_channel_id"),
            "output_channel": row.get("output_channel_id"),
            "anonymity": bool(row.get("anonymity", 1)),
            "cooldown": row.get("cooldown", 30),
            "next_id": row.get("next_id", 1)
        }

    async def update_config(self, guild_id, **kwargs):
        data = {"guild_id": str(guild_id)}
        data.update(kwargs)
        await self.bot.db_manager.upsert("confession_config", data, on_conflict="guild_id")

    async def increment_id(self, guild_id):
        cfg = await self.get_config(guild_id)
        if not cfg:
            return 1
        new_id = cfg["next_id"] + 1
        await self.bot.db_manager.update(
            "confession_config",
            {"guild_id": str(guild_id)},
            {"next_id": new_id},
        )
        return new_id - 1

    # ----- ГОЛ БОЛОВСРУУЛАЛТ -----
    async def process_confession(self, user, guild, content, interaction=None):
        cfg = await self.get_config(guild.id)
        if not cfg:
            if interaction:
                await interaction.followup.send("❌ Систем тохируулагдаагүй. `/confess_setup`-ээр тохируулна уу.", ephemeral=True)
            return

        now = int(datetime.datetime.now().timestamp())
        # Күүдаун шалгах
        cd_row = await self.bot.db_manager.fetch_one(
            "confession_cooldown", {"user_id": str(user.id), "guild_id": str(guild.id)}
        )
        last_time = cd_row.get("last_time", 0) if cd_row else 0
        if last_time and now - last_time < cfg["cooldown"]:
            remaining = cfg["cooldown"] - (now - last_time)
            msg = f"⏳ Та {remaining} секундын дараа дахин илгээх боломжтой."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                try: await user.send(msg)
                except: pass
            return

        # Хар жагсаалт шалгах
        blacklist_rows = await self.bot.db_manager.fetch_all("confession_blacklist", {"guild_id": str(guild.id)})
        blacklist = [r.get("word", "") for r in blacklist_rows]
        for w in blacklist:
            if w in content.lower():
                msg = "🚫 Таны захиа хориотой үг агуулж байна."
                if interaction:
                    await interaction.followup.send(msg, ephemeral=True)
                else:
                    try: await user.send(msg)
                    except: pass
                return

        # Гаралтын сувагт илгээх
        output_channel = guild.get_channel(cfg["output_channel"])
        if not output_channel:
            if interaction:
                await interaction.followup.send("❌ Гаралтын суваг олдсонгүй.", ephemeral=True)
            return

        # ID авах
        confess_id = await self.increment_id(guild.id)

        author_name = "Anonymous" if cfg["anonymity"] else user.display_name
        embed = discord.Embed(
            title=f"📩 Confession #{confess_id}",
            description=content,
            color=GOLD_COLOR,
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"Илгээсэн: {author_name}")

        sent_msg = await output_channel.send(embed=embed)

        # Күүдаун бүртгэх + түүх хадгалах
        await self.bot.db_manager.insert("confession_messages", {
            "guild_id": str(guild.id),
            "confession_id": confess_id,
            "message_id": str(sent_msg.id),
            "user_id": str(user.id),
            "content": content[:500],
        })
        await self.bot.db_manager.upsert(
            "confession_cooldown",
            {"user_id": str(user.id), "guild_id": str(guild.id), "last_time": now},
            on_conflict="user_id,guild_id",
        )

        # Даалгаврын системд мэдэгдэх
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(user.id, guild.id, "confession_write", 1)

        # Хэрэглэгчид амжилттай илгээсэн тухай мэдэгдэх
        if interaction:
            await interaction.followup.send(f"✅ Таны нууц захиа (#{confess_id}) амжилттай илгээгдлээ.", ephemeral=True)
        else:
            try: await user.send(f"✅ Таны нууц захиа (#{confess_id}) амжилттай илгээгдлээ.")
            except: pass

    # ----- SLASH COMMANDS -----
    @app_commands.command(name="confess", description="Нууц захиа илгээх (модал)")
    async def confess_slash(self, interaction: discord.Interaction):
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            await interaction.response.send_message("❌ Систем тохируулагдаагүй. `/confess_setup`-ээр тохируулна уу.", ephemeral=True)
            return
        modal = ConfessionModal(self, interaction)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="confess_setup", description="Нууц захианы тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def confess_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_config(interaction.guild_id)
        view = SetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="confess_blacklist", description="Хориотой үг удирдах")
    @app_commands.default_permissions(administrator=True)
    async def confess_blacklist(self, interaction: discord.Interaction, action: str, word: str = None):
        await interaction.response.defer(ephemeral=True)
        if action.lower() == "add":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            await self.bot.db_manager.upsert(
                "confession_blacklist",
                {"guild_id": str(interaction.guild_id), "word": word.lower()},
                on_conflict="guild_id,word",
            )
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтад нэмэгдлээ.", ephemeral=True)
        elif action.lower() == "remove":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            await self.bot.db_manager.delete(
                "confession_blacklist",
                {"guild_id": str(interaction.guild_id), "word": word.lower()},
            )
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтаас хасагдлаа.", ephemeral=True)
        elif action.lower() == "list":
            rows = await self.bot.db_manager.fetch_all(
                "confession_blacklist", {"guild_id": str(interaction.guild_id)}
            )
            if not rows:
                await interaction.followup.send("📭 Хориотой үг байхгүй.", ephemeral=True)
            else:
                words = ", ".join([f"`{r.get('word', '')}`" for r in rows])
                await interaction.followup.send(f"🚫 Хориотой үгс: {words}", ephemeral=True)
        else:
            await interaction.followup.send("❌ `add`, `remove`, `list` сонголтыг ашиглана уу.", ephemeral=True)

    @app_commands.command(name="confess_delete", description="Нууц захиаг устгах (админ)")
    @app_commands.default_permissions(administrator=True)
    async def confess_delete(self, interaction: discord.Interaction, confession_id: int):
        await interaction.response.defer(ephemeral=False)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send("❌ Систем тохируулагдаагүй.", ephemeral=True)
        msg_row = await self.bot.db_manager.fetch_one(
            "confession_messages",
            {"guild_id": str(interaction.guild_id), "confession_id": confession_id},
        )
        if not msg_row:
            return await interaction.followup.send(f"❌ #{confession_id} олдсонгүй.", ephemeral=True)
        msg_id, user_id, content = msg_row.get("message_id"), msg_row.get("user_id"), msg_row.get("content", "")
        channel = interaction.guild.get_channel(cfg["output_channel"])
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass
        await self.bot.db_manager.delete(
            "confession_messages",
            {"guild_id": str(interaction.guild_id), "confession_id": confession_id},
        )
        embed = discord.Embed(title="🗑️ Захиа устгагдлаа",
                              description=f"Захиа #{confession_id} устгагдсан.\nАгуулга: {content[:100]}...",
                              color=WARNING_COLOR)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="confess_stats", description="Нууц захианы системийн статистик")
    async def confess_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        cfg = await self.get_config(interaction.guild_id)
        if not cfg:
            return await interaction.followup.send("❌ Систем тохируулагдаагүй.", ephemeral=True)
        cooldown_rows = await self.bot.db_manager.fetch_all(
            "confession_cooldown", {"guild_id": str(interaction.guild_id)}
        )
        active = len(cooldown_rows)
        msg_rows = await self.bot.db_manager.fetch_all(
            "confession_messages", {"guild_id": str(interaction.guild_id)}
        )
        total_msgs = len(msg_rows)
        embed = discord.Embed(
            title="📊 Нууц захианы статистик",
            color=INFO_COLOR,
            description=f"**Нийт илгээгдсэн:** {cfg['next_id'] - 1}\n**Идэвхтэй күүдаун:** {active}\n**Хадгалагдсан мессеж:** {total_msgs}\n**Аноним:** {'Идэвхтэй' if cfg['anonymity'] else 'Унтарсан'}\n**Күүдаун:** {cfg['cooldown']}s"
        )
        await interaction.followup.send(embed=embed)

    # ----- СУВГАНЫ СОНСГОЛ -----
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        cfg = await self.get_config(message.guild.id)
        if not cfg or message.channel.id != cfg["confess_channel"]:
            return
        await self.process_confession(user=message.author, guild=message.guild, content=message.content)
        try:
            await message.delete()
        except:
            pass

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

async def setup(bot):
    await bot.add_cog(Confessions(bot))
