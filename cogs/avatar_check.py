from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands
import datetime

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

class ConfigView(discord.ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)  # 10 минутын дараа идэвхгүй болно
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Та энэ тохиргоог удирдах эрхгүй.", ephemeral=True)
            return False
        return True

    async def update_embed(self, interaction: discord.Interaction):
        cfg = await self.cog.get_config(self.guild_id)
        embed = self._build_embed(cfg, interaction.guild)
        await interaction.response.edit_message(embed=embed, view=self)

    def _build_embed(self, cfg, guild):
        if cfg is None:
            desc = "⚠️ **Лог суваг тохируулаагүй.**\nДоорх цэсээр сувгаа сонгоно уу."
            channel_text = "❌ Суваг олдсонгүй"
            enabled = False
        else:
            channel_id = cfg.get("channel_id")
            channel = guild.get_channel(channel_id) if channel_id else None
            channel_text = channel.mention if channel else f"`{channel_id}` (олдсонгүй)"
            enabled = cfg["enabled"]
            desc = f"**Лог суваг:** {channel_text}\n**Төлөв:** {'✅ Идэвхтэй' if enabled else '❌ Унтарсан'}"

        embed = discord.Embed(
            title="🔧 Аватар логын тохиргоо",
            description=desc,
            color=SUCCESS_COLOR if enabled else WARNING_COLOR
        )
        embed.set_footer(text="Суваг сонгох, төлөв өөрчлөх эсвэл шинэчлэх товчлуурыг ашиглана уу.")
        return embed

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="Лог сувгаа сонго...", min_values=1, max_values=1)
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        await interaction.response.defer()
        channel = select.values[0]
        await self.cog.set_config(self.guild_id, channel_id=channel.id)
        cfg = await self.cog.get_config(self.guild_id)
        embed = self._build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed)

    @discord.ui.button(label="Toggle Enabled", style=discord.ButtonStyle.primary, row=1)
    async def toggle_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        cfg = await self.cog.get_config(self.guild_id)
        if cfg is None:
            await interaction.followup.send("❌ Эхлээд лог сувгаа сонгоно уу!", ephemeral=True)
            return
        new_state = not cfg["enabled"]
        await self.cog.set_config(self.guild_id, enabled=new_state)
        cfg = await self.cog.get_config(self.guild_id)
        embed = self._build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed)

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.secondary, row=1)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        cfg = await self.cog.get_config(self.guild_id)
        embed = self._build_embed(cfg, interaction.guild)
        await interaction.edit_original_response(embed=embed)


class AvatarLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== ӨГӨГДЛИЙН САН ====================
    async def init_db(self):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute('''CREATE TABLE IF NOT EXISTS avatar_log_config (
                    guild_id VARCHAR(255) PRIMARY KEY,
                    log_channel_id BIGINT,
                    enabled TINYINT(1) DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4''')

    async def get_config(self, guild_id):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT log_channel_id, enabled FROM avatar_log_config WHERE guild_id = %s",
                    (str(guild_id),)
                )
                row = await cur.fetchone()
        if not row:
            return None
        return {"channel_id": row[0], "enabled": bool(row[1])}

    async def set_config(self, guild_id, channel_id=None, enabled=None):
        async with self.bot.db.acquire() as conn:
            async with conn.cursor() as cur:
                current = await self.get_config(guild_id)
                if current:
                    new_channel = channel_id if channel_id is not None else current["channel_id"]
                    new_enabled = enabled if enabled is not None else current["enabled"]
                    await cur.execute(
                        "UPDATE avatar_log_config SET log_channel_id = %s, enabled = %s WHERE guild_id = %s",
                        (new_channel, 1 if new_enabled else 0, str(guild_id))
                    )
                else:
                    if channel_id is None:
                        return
                    await cur.execute(
                        "INSERT INTO avatar_log_config (guild_id, log_channel_id, enabled) VALUES (%s, %s, %s)",
                        (str(guild_id), channel_id, 1 if enabled is None or enabled else 0)
                    )

    # ==================== КОМАНД ====================
    @commands.hybrid_command(name="avatar_config", description="Аватар логын тохиргооны самбар (embed + button)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def avatar_config(self, ctx: commands.Context):
        await ctx.defer(ephemeral=False)
        await self.init_db()
        cfg = await self.get_config(ctx.guild.id)
        view = ConfigView(self, ctx.guild.id, ctx.author.id)
        embed = view._build_embed(cfg, ctx.guild)
        await ctx.send(embed=embed, view=view)

    # ==================== EVENT ====================
    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.display_avatar.url == after.display_avatar.url:
            return

        # Quests системийг дуудах
        quests_cog = self.bot.get_cog("Quests")

        for guild in self.bot.guilds:
            member = guild.get_member(after.id)
            if not member:
                continue
            cfg = await self.get_config(guild.id)
            if not cfg or not cfg["enabled"]:
                continue
            channel = guild.get_channel(cfg["channel_id"])
            if not channel:
                continue

            # Даалгаврын прогресс нэмэгдүүлэх
            if quests_cog:
                await quests_cog.trigger_event(member.id, guild.id, "avatar_change", 1)

            embed = discord.Embed(
                title="🔄 Аватар өөрчлөгдлөө",
                description=f"{member.mention} (`{member}`) аватараа шинэчлэв.",
                color=GOLD_COLOR,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_author(name=member.display_name, icon_url=after.display_avatar.url)
            embed.set_thumbnail(url=before.display_avatar.url)
            embed.set_image(url=after.display_avatar.url)
            embed.add_field(name="🖼️ Хуучин аватар", value=f"[Харах]({before.display_avatar.url})", inline=True)
            embed.add_field(name="🆕 Шинэ аватар", value=f"[Харах]({after.display_avatar.url})", inline=True)
            embed.set_footer(text=f"ID: {after.id}")
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                pass

    async def cog_load(self):
        await self.init_db()

async def setup(bot):
    await bot.add_cog(AvatarLogger(bot))
