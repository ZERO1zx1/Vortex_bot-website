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

    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''CREATE TABLE IF NOT EXISTS confession_config (
                    guild_id VARCHAR(255) PRIMARY KEY,
                    confess_channel_id BIGINT,
                    output_channel_id BIGINT,
                    anonymity TINYINT(1) DEFAULT 1,
                    cooldown INT DEFAULT 30,
                    next_id INT DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                await cur.execute('''CREATE TABLE IF NOT EXISTS confession_blacklist (
                    guild_id VARCHAR(255),
                    word VARCHAR(255),
                    PRIMARY KEY (guild_id, word)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                await cur.execute('''CREATE TABLE IF NOT EXISTS confession_cooldown (
                    user_id VARCHAR(255),
                    guild_id VARCHAR(255),
                    last_time BIGINT,
                    PRIMARY KEY (user_id, guild_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')
                await cur.execute('''CREATE TABLE IF NOT EXISTS confession_messages (
                    guild_id VARCHAR(255),
                    confession_id INT,
                    message_id BIGINT,
                    user_id VARCHAR(255),
                    content TEXT,
                    PRIMARY KEY (guild_id, confession_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    # ----- DB туслахууд -----
    async def get_config(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT confess_channel_id, output_channel_id, anonymity, cooldown, next_id FROM confession_config WHERE guild_id = %s",
                    (str(guild_id),)
                )
                row = await cur.fetchone()
        if not row:
            return None
        return {
            "confess_channel": row[0],
            "output_channel": row[1],
            "anonymity": bool(row[2]),
            "cooldown": row[3],
            "next_id": row[4]
        }

    async def update_config(self, guild_id, **kwargs):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1 FROM confession_config WHERE guild_id = %s", (str(guild_id),))
                exists = await cur.fetchone()
                if exists:
                    set_clause = ", ".join([f"{k} = %s" for k in kwargs])
                    values = list(kwargs.values()) + [str(guild_id)]
                    await cur.execute(f"UPDATE confession_config SET {set_clause} WHERE guild_id = %s", values)
                else:
                    cols = ", ".join(kwargs.keys())
                    placeholders = ", ".join(["%s"] * len(kwargs))
                    await cur.execute(f"INSERT INTO confession_config (guild_id, {cols}) VALUES (%s, {placeholders})",
                                      [str(guild_id)] + list(kwargs.values()))

    async def increment_id(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("UPDATE confession_config SET next_id = next_id + 1 WHERE guild_id = %s", (str(guild_id),))
                await cur.execute("SELECT next_id - 1 FROM confession_config WHERE guild_id = %s", (str(guild_id),))
                row = await cur.fetchone()
                return row[0] if row else 1

    # ----- ГОЛ БОЛОВСРУУЛАЛТ -----
    async def process_confession(self, user, guild, content, interaction=None):
        cfg = await self.get_config(guild.id)
        if not cfg:
            if interaction:
                await interaction.followup.send("❌ Систем тохируулагдаагүй. `/confess_setup`-ээр тохируулна уу.", ephemeral=True)
            return

        now = int(datetime.datetime.now().timestamp())
        # Күүдаун шалгах
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT last_time FROM confession_cooldown WHERE user_id = %s AND guild_id = %s",
                                  (str(user.id), str(guild.id)))
                row = await cur.fetchone()
        if row and now - row[0] < cfg["cooldown"]:
            remaining = cfg["cooldown"] - (now - row[0])
            msg = f"⏳ Та {remaining} секундын дараа дахин илгээх боломжтой."
            if interaction:
                await interaction.followup.send(msg, ephemeral=True)
            else:
                try: await user.send(msg)
                except: pass
            return

        # Хар жагсаалт шалгах
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT word FROM confession_blacklist WHERE guild_id = %s", (str(guild.id),))
                blacklist = [r[0] for r in await cur.fetchall()]
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
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "INSERT INTO confession_messages (guild_id, confession_id, message_id, user_id, content) VALUES (%s, %s, %s, %s, %s)",
                    (str(guild.id), confess_id, sent_msg.id, str(user.id), content[:500])
                )
                await cur.execute(
                    "INSERT INTO confession_cooldown (user_id, guild_id, last_time) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE last_time = %s",
                    (str(user.id), str(guild.id), now, now)
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
        await self.init_db()
        cfg = await self.get_config(interaction.guild_id)
        view = SetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="confess_blacklist", description="Хориотой үг удирдах")
    @app_commands.default_permissions(administrator=True)
    async def confess_blacklist(self, interaction: discord.Interaction, action: str, word: str = None):
        await interaction.response.defer(ephemeral=True)
        await self.init_db()
        if action.lower() == "add":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("INSERT IGNORE INTO confession_blacklist (guild_id, word) VALUES (%s, %s)",
                                      (str(interaction.guild_id), word.lower()))
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтад нэмэгдлээ.", ephemeral=True)
        elif action.lower() == "remove":
            if not word:
                return await interaction.followup.send("❌ Үг оруулна уу.", ephemeral=True)
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("DELETE FROM confession_blacklist WHERE guild_id = %s AND word = %s",
                                      (str(interaction.guild_id), word.lower()))
            await interaction.followup.send(f"✅ `{word}` хар жагсаалтаас хасагдлаа.", ephemeral=True)
        elif action.lower() == "list":
            async with self.bot.db.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT word FROM confession_blacklist WHERE guild_id = %s", (str(interaction.guild_id),))
                    rows = await cur.fetchall()
            if not rows:
                await interaction.followup.send("📭 Хориотой үг байхгүй.", ephemeral=True)
            else:
                words = ", ".join([f"`{r[0]}`" for r in rows])
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
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT message_id, user_id, content FROM confession_messages WHERE guild_id = %s AND confession_id = %s",
                    (str(interaction.guild_id), confession_id)
                )
                row = await cur.fetchone()
        if not row:
            return await interaction.followup.send(f"❌ #{confession_id} олдсонгүй.", ephemeral=True)
        msg_id, user_id, content = row
        channel = interaction.guild.get_channel(cfg["output_channel"])
        if channel:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.delete()
            except:
                pass
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DELETE FROM confession_messages WHERE guild_id = %s AND confession_id = %s",
                                  (str(interaction.guild_id), confession_id))
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
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT COUNT(*) FROM confession_cooldown WHERE guild_id = %s", (str(interaction.guild_id),))
                active = (await cur.fetchone())[0]
                await cur.execute("SELECT COUNT(*) FROM confession_messages WHERE guild_id = %s", (str(interaction.guild_id),))
                total_msgs = (await cur.fetchone())[0]
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
        await self.init_db()

async def setup(bot):
    await bot.add_cog(Confessions(bot))
