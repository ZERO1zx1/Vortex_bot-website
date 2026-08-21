from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands, tasks
from discord import app_commands, ui
from datetime import datetime, timedelta, timezone
import re

EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# Хугацаа задлагч
def parse_duration(duration_str: str) -> int:
    match = re.match(r"(\d+)([smhdw])", duration_str.lower())
    if not match:
        raise ValueError("Хүчингүй формат: жишээ нь 30s, 5m, 2h, 1d, 1w")
    value = int(match.group(1))
    unit = match.group(2)
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    return value * multipliers[unit]

class RoleManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_unload(self):
        try:
            self.temprole_loop.cancel()
        except:
            pass

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        self.temprole_loop.start()

    def can_manage_role(self, guild, role):
        bot_member = guild.me
        return (bot_member.guild_permissions.manage_roles and
                role.position < bot_member.top_role.position)

    # ══════════════ ROLE GROUP (БАЙНГЫН ҮҮРЭГ) ══════════════
    @commands.hybrid_group(name='role', description="Байнгын үүрэг удирдах",
                           with_app_command=True, invoke_without_command=True)
    async def role_group(self, ctx):
        embed = discord.Embed(
            title="🎭 Үүрэг удирдлага",
            description="`/role give @хэрэглэгч @үүрэг` – үүрэг өгөх\n"
                        "`/role remove @хэрэглэгч @үүрэг` – үүрэг хасах\n"
                        "`/role info @үүрэг` – үүргийн мэдээлэл\n"
                        "`/role members @үүрэг` – үүрэгтэй гишүүд",
            color=INFO_COLOR
        )
        embed.set_footer(text="Байнгын үүрэг (хугацаагүй)")
        await ctx.send(embed=embed)

    @role_group.command(name='give', description="Хэрэглэгчид байнгын үүрэг өгөх")
    @app_commands.describe(user="Хэрэглэгч", role="Үүрэг")
    @commands.has_permissions(manage_roles=True)
    async def role_give(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(title="❌ Үүрэг удирдах боломжгүй",
                                  description="Бот энэ үүргийг удирдах эрхгүй (үүрэг өндөр эсвэл эрх дутуу).",
                                  color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if role in user.roles:
            embed = discord.Embed(title="⚠️ Аль хэдийн бий",
                                  description=f"{user.mention} -д {role.mention} үүрэг байгаа.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        await user.add_roles(role, reason=f"{ctx.author} өгсөн")
        embed = discord.Embed(title="✅ Үүрэг өглөө",
                              description=f"{user.mention} -д {role.mention} үүрэг өглөө.", color=SUCCESS_COLOR)
        await ctx.send(embed=embed)

        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "role_give", 1)

    @role_group.command(name='remove', description="Хэрэглэгчээс байнгын үүрэг хасах")
    @app_commands.describe(user="Хэрэглэгч", role="Үүрэг")
    @commands.has_permissions(manage_roles=True)
    async def role_remove(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(title="❌ Үүрэг удирдах боломжгүй",
                                  description="Бот энэ үүргийг удирдах эрхгүй (үүрэг өндөр эсвэл эрх дутуу).",
                                  color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if role not in user.roles:
            embed = discord.Embed(title="⚠️ Үүрэг байхгүй",
                                  description=f"{user.mention} -д {role.mention} үүрэг байхгүй.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        await user.remove_roles(role, reason=f"{ctx.author} хассан")
        embed = discord.Embed(title="✅ Үүрэг хасагдлаа",
                              description=f"{user.mention} -ээс {role.mention} үүрэг хасагдлаа.", color=SUCCESS_COLOR)
        await ctx.send(embed=embed)

    @role_group.command(name='info', description="Үүргийн дэлгэрэнгүй мэдээлэл")
    @app_commands.describe(role="Мэдээлэл харах үүрэг")
    async def role_info(self, ctx, role: discord.Role):
        embed = discord.Embed(title=f"📌 {role.name} үүргийн мэдээлэл", color=role.color)
        embed.add_field(name="🆔 ID", value=role.id, inline=True)
        embed.add_field(name="🎨 Өнгө", value=str(role.color), inline=True)
        embed.add_field(name="📊 Байрлал", value=role.position, inline=True)
        embed.add_field(name="👥 Гишүүдийн тоо", value=len(role.members), inline=True)
        embed.add_field(name="📅 Үүсгэсэн", value=discord.utils.format_dt(role.created_at, style="F"), inline=True)
        embed.add_field(name="📯 Дурдах боломжтой", value="Тийм" if role.mentionable else "Үгүй", inline=True)
        embed.add_field(name="🔒 Админ эрх", value="Тийм" if role.permissions.administrator else "Үгүй", inline=True)
        await ctx.send(embed=embed)

    @role_group.command(name='members', description="Тухайн үүрэгтэй гишүүдийн жагсаалт")
    @app_commands.describe(role="Гишүүдийг харах үүрэг")
    async def role_members(self, ctx, role: discord.Role):
        members = role.members
        if not members:
            return await ctx.send(embed=discord.Embed(description=f"{role.mention} үүрэгтэй гишүүн байхгүй.", color=WARNING_COLOR))
        # Хуудаслалттай харуулах (энгийн жишээ)
        member_list = [m.mention for m in members[:30]]
        embed = discord.Embed(title=f"👥 {role.name} үүрэгтэй гишүүд ({len(members)})",
                              description=", ".join(member_list),
                              color=role.color)
        await ctx.send(embed=embed)

    # ══════════════ TEMPROLE GROUP (ТҮР ҮҮРЭГ) ══════════════
    @commands.hybrid_group(name='temprole', description="Түр хугацааны үүрэг удирдах",
                           with_app_command=True, invoke_without_command=True)
    async def temprole_group(self, ctx):
        embed = discord.Embed(
            title="⏱️ Түр үүрэг удирдлага",
            description="`/temprole give @хэрэглэгч @үүрэг 1h` – түр үүрэг өгөх\n"
                        "`/temprole remove @хэрэглэгч @үүрэг` – хугацаанаас өмнө хасах\n"
                        "`/temprole list [@хэрэглэгч]` – идэвхтэй түр үүргүүд\n"
                        "`/temprole clear @хэрэглэгч` – бүх түр үүргийг цуцлах",
            color=INFO_COLOR
        )
        embed.add_field(name="Хугацааны формат", value="`30s`, `5m`, `2h`, `1d`, `1w`", inline=False)
        embed.set_footer(text="Хугацаа дуусахад үүрэг автоматаар хасагдана")
        await ctx.send(embed=embed)

    @temprole_group.command(name='give', description="Түр үүрэг өгөх (хугацаатай)")
    @app_commands.describe(user="Хэрэглэгч", role="Үүрэг", duration="Хугацаа (30s, 5m, 2h, 1d, 1w)")
    @commands.has_permissions(manage_roles=True)
    async def temprole_give(self, ctx, user: discord.Member, role: discord.Role, duration: str):
        await ctx.defer(ephemeral=False)
        if not self.can_manage_role(ctx.guild, role):
            embed = discord.Embed(title="❌ Үүрэг удирдах боломжгүй",
                                  description="Бот энэ үүргийг удирдах эрхгүй.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        try:
            seconds = parse_duration(duration)
        except ValueError as e:
            embed = discord.Embed(title="❌ Хүчингүй хугацаа", description=str(e), color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        if seconds <= 0:
            embed = discord.Embed(title="❌ Хүчингүй хугацаа", description="Эерэг тоо оруулна уу.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        cfg = await self.bot.db_manager.fetch_one("temprole_config", {"guild_id": str(ctx.guild.id)})
        max_sec = cfg.get("max_duration_seconds", 604800) if cfg else 604800
        if seconds > max_sec:
            embed = discord.Embed(title="❌ Хэт урт хугацаа",
                                  description=f"Энэ серверт түр үүргийн хамгийн их хугацаа {max_sec//86400} хоног байна.",
                                  color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        end_time = int((datetime.now(timezone.utc) + timedelta(seconds=seconds)).timestamp())

        existing = await self.bot.db_manager.fetch_one(
            "temproles",
            {"user_id": str(user.id), "guild_id": str(ctx.guild.id), "role_id": str(role.id)},
        )
        if existing:
            await self.bot.db_manager.update(
                "temproles",
                {"user_id": str(user.id), "guild_id": str(ctx.guild.id), "role_id": str(role.id)},
                {"end_time": end_time},
            )
        else:
            await self.bot.db_manager.insert("temproles", {
                "user_id": str(user.id),
                "guild_id": str(ctx.guild.id),
                "role_id": str(role.id),
                "end_time": end_time,
            })

        if role not in user.roles:
            try:
                await user.add_roles(role, reason=f"Түр үүрэг ({duration}) өгсөн: {ctx.author}")
            except discord.Forbidden:
                embed = discord.Embed(title="❌ Эрх хүрэхгүй",
                                      description="Ботод 'Manage Roles' эрх байхгүй эсвэл үүрэг ботын хамгийн өндөр үүргээс дээгүүр байна.",
                                      color=ERROR_COLOR)
                return await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(title="❌ Алдаа", description=str(e), color=ERROR_COLOR)
                return await ctx.send(embed=embed)

        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        parts = []
        if days: parts.append(f"{days} өдөр")
        if hours: parts.append(f"{hours} цаг")
        if minutes: parts.append(f"{minutes} минут")
        if secs: parts.append(f"{secs} секунд")
        time_str = " ".join(parts) if parts else "0 секунд"

        embed = discord.Embed(
            title="⏱️ Түр үүрэг өглөө",
            description=f"{user.mention} -д {role.mention} үүрэг **{time_str}** хугацаагаар өглөө.",
            color=SUCCESS_COLOR
        )
        embed.set_footer(text=f"Дуусах: {datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=embed)

        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "role_give", 1)

    @temprole_group.command(name='remove', description="Түр үүргийг хугацаанаас өмнө хасах")
    @app_commands.describe(user="Хэрэглэгч", role="Үүрэг")
    @commands.has_permissions(manage_roles=True)
    async def temprole_remove(self, ctx, user: discord.Member, role: discord.Role):
        await ctx.defer(ephemeral=False)
        entry = await self.bot.db_manager.fetch_one(
            "temproles",
            {"user_id": str(user.id), "guild_id": str(ctx.guild.id), "role_id": str(role.id)},
        )
        if not entry:
            embed = discord.Embed(title="⚠️ Түр үүрэг биш",
                                  description=f"{user.mention} -д {role.mention} нь түр үүрэг биш (өгөгдлийн санд байхгүй).",
                                  color=WARNING_COLOR)
            return await ctx.send(embed=embed)

        await self.bot.db_manager.delete(
            "temproles",
            {"user_id": str(user.id), "guild_id": str(ctx.guild.id), "role_id": str(role.id)},
        )

        if role in user.roles:
            try:
                await user.remove_roles(role, reason=f"Түр үүрэг эрт хасагдсан: {ctx.author}")
            except discord.Forbidden:
                embed = discord.Embed(title="❌ Эрх хүрэхгүй", description="Ботод 'Manage Roles' эрх байхгүй.", color=ERROR_COLOR)
                return await ctx.send(embed=embed)
            except discord.HTTPException as e:
                embed = discord.Embed(title="❌ Алдаа", description=str(e), color=ERROR_COLOR)
                return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="✅ Түр үүрэг хасагдлаа",
            description=f"{user.mention} -ээс {role.mention} үүрэг эрт хасагдлаа.",
            color=SUCCESS_COLOR
        )
        await ctx.send(embed=embed)

    @temprole_group.command(name='list', description="Идэвхтэй түр үүргүүдийн жагсаалт")
    @app_commands.describe(user="Тухайн хэрэглэгчийн түр үүргүүд (хоосон орхивол бүгд)")
    async def temprole_list(self, ctx, user: discord.Member = None):
        await ctx.defer()
        if user:
            rows = await self.bot.db_manager.fetch_all(
                "temproles",
                {"guild_id": str(ctx.guild.id), "user_id": str(user.id)},
                order_by="end_time",
            )
            rows = [(r["role_id"], r["end_time"]) for r in rows]
        else:
            rows = await self.bot.db_manager.fetch_all(
                "temproles",
                {"guild_id": str(ctx.guild.id)},
                order_by="end_time",
            )
            rows = [(r["user_id"], r["role_id"], r["end_time"]) for r in rows]

        if not rows:
            return await ctx.send(embed=discord.Embed(description="ℹ️ Идэвхтэй түр үүрэг байхгүй.", color=INFO_COLOR))

        embed = discord.Embed(title="⏱️ Идэвхтэй түр үүргүүд", color=INFO_COLOR)
        if user:
            for role_id, end_time in rows:
                role = ctx.guild.get_role(role_id)
                role_name = role.mention if role else f"<@&{role_id}>"
                embed.add_field(name=role_name,
                                value=f"Дуусах: {discord.utils.format_dt(datetime.fromtimestamp(end_time), style='R')}",
                                inline=False)
        else:
            # Бүгдийг харуулахдаа эхний 20-г харуулна
            for uid, rid, end_time in rows[:20]:
                member = ctx.guild.get_member(int(uid))
                user_str = member.mention if member else f"<@{uid}>"
                role = ctx.guild.get_role(rid)
                role_str = role.mention if role else f"<@&{rid}>"
                embed.add_field(name=f"{user_str} → {role_str}",
                                value=f"Дуусах: {discord.utils.format_dt(datetime.fromtimestamp(end_time), style='R')}",
                                inline=False)
        await ctx.send(embed=embed)

    @temprole_group.command(name='clear', description="Хэрэглэгчийн бүх түр үүргийг цуцлах")
    @app_commands.describe(user="Түр үүргүүдийг нь цуцлах хэрэглэгч")
    @commands.has_permissions(manage_roles=True)
    async def temprole_clear(self, ctx, user: discord.Member):
        await ctx.defer()
        rows = await self.bot.db_manager.fetch_all(
            "temproles", {"guild_id": str(ctx.guild.id), "user_id": str(user.id)}
        )
        if not rows:
            return await ctx.send(embed=discord.Embed(description=f"{user.mention} -д түр үүрэг байхгүй.", color=WARNING_COLOR))
        for r in rows:
            rid = r.get("role_id")
            role = ctx.guild.get_role(rid)
            if role and role in user.roles:
                try:
                    await user.remove_roles(role, reason=f"Түр үүргүүд цуцлагдсан: {ctx.author}")
                except:
                    pass
        await self.bot.db_manager.delete(
            "temproles", {"guild_id": str(ctx.guild.id), "user_id": str(user.id)}
        )
        await ctx.send(embed=discord.Embed(description=f"✅ {user.mention} -н бүх түр үүрэг цуцлагдлаа.", color=SUCCESS_COLOR))

    # ══════════════ TEMPROLE CONFIG ══════════════
    @app_commands.command(name="temprole_config", description="Түр үүргийн тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def temprole_config(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = TemproleConfigView(self, interaction.guild_id, interaction.user.id)
        row = await self.bot.db_manager.fetch_one("temprole_config", {"guild_id": str(interaction.guild_id)})
        max_sec = row.get("max_duration_seconds", 604800) if row else 604800
        embed = discord.Embed(title="⏱️ Түр үүргийн тохиргоо", color=INFO_COLOR)
        embed.add_field(name="Хамгийн их хугацаа", value=f"{max_sec // 86400} хоног ({max_sec} секунд)", inline=False)
        embed.set_footer(text="Доорх товчлуураар тохиргоог өөрчилнө үү")
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    # ══════════════ TEMPROLE LOOP ══════════════
    @tasks.loop(minutes=1.0)
    async def temprole_loop(self):
        await self.bot.wait_until_ready()
        now = int(datetime.now(timezone.utc).timestamp())
        rows = await self.bot.db_manager.fetch_safe("temproles", {})
        expired = [r for r in rows if (r.get("end_time") or 0) <= now]

        for r in expired:
            eid = r.get("id")
            uid = r.get("user_id")
            gid = r.get("guild_id")
            rid = r.get("role_id")
            guild = self.bot.get_guild(int(gid))
            if guild:
                user = guild.get_member(int(uid))
                role = guild.get_role(rid)
                if user and role and role in user.roles:
                    try:
                        await user.remove_roles(role, reason="Түр үүрэг хугацаа дууссан")
                    except (discord.Forbidden, discord.HTTPException):
                        pass
            await self.bot.db_manager.delete("temproles", {"id": eid})


# ══════════════ VIEW / MODAL ══════════════
class TemproleConfigView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    @ui.button(label="⚙️ Хамгийн их хугацаа тохируулах", style=discord.ButtonStyle.secondary)
    async def set_max_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MaxDurationModal(self))

class MaxDurationModal(ui.Modal, title="Хамгийн их хугацаа (өдөр)"):
    days = ui.TextInput(label="Хоног (тоо)", placeholder="Жишээ: 7", required=True)

    def __init__(self, view):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = int(self.days.value)
            if days <= 0:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Эерэг бүхэл тоо оруулна уу.", ephemeral=True)
        seconds = days * 86400
        await self.view.cog.bot.db_manager.upsert(
            "temprole_config",
            {"guild_id": str(interaction.guild_id), "max_duration_seconds": seconds},
            on_conflict="guild_id",
        )
        await interaction.response.send_message(f"✅ Хамгийн их хугацаа: {days} хоног боллоо.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RoleManagement(bot))