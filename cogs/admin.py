import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timezone
import time
import platform
import psutil

from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
from utils.slash_context import SlashContext
from utils.embed_style import style_embed, add_box_field, error_embed, gold_embed

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def is_owner_or_co_owner(self, user_id):
        return user_id in self.bot.owner_ids

    @app_commands.command(name='status', description='Check bot status and health')
    async def status(self, interaction):
        ctx = SlashContext(interaction)
        await ctx.defer()
        uptime = str(datetime.fromtimestamp(self.start_time, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
        latency_ms = self.bot.latency * 1000
        latency = round(latency_ms) if latency_ms == latency_ms else 0
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent

        embed = style_embed("Бот-ын төлөв", "Системын мэдээлэл", INFO_COLOR, "info")
        add_box_field(embed, "СЭЙТЭРХҮҮ", [
            f"╭ Ажилласан хугацаа\n╰→ {uptime}",
            f"╭ Хоцролт\n╰→ {latency}ms",
            f"╭ CPU ашиглалт\n╰→ {cpu_usage}%",
            f"╭ RAM ашиглалт\n╰→ {ram_usage}%",
            f"╭ Операцион систем\n╰→ {platform.system()}",
            f"╭ Python хувилбар\n╰→ {platform.python_version()}",
        ])
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='info', description='Серверийн мэдээлэл харах')
    async def info(self, interaction):
        ctx = SlashContext(interaction)
        await ctx.defer(ephemeral=False)
        if ctx.guild is None:
            return await ctx.send(embed=error_embed("АЛДАА", "Зөвхөн сервер дотор ашиглах боломжтой."))

        guild = ctx.guild
        total_members = guild.member_count
        humans = len([m for m in guild.members if not m.bot])
        bots = total_members - humans
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles) - 1
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0
        verif_levels = {
            discord.VerificationLevel.none: "❌ Хязгаарлалтгүй",
            discord.VerificationLevel.low: "✅ Бага",
            discord.VerificationLevel.medium: "⚠️ Дунд",
            discord.VerificationLevel.high: "🔒 Өндөр",
            discord.VerificationLevel.highest: "🔒🔒 Хамгийн өндөр"
        }
        verif_level = verif_levels.get(guild.verification_level, "Тодорхойгүй")

        color = GOLD_COLOR if guild.premium_tier > 0 else EMBED_COLOR
        embed = style_embed(guild.name, "Серверийн дэлгэрэнгүй мэдээлэл", color, "info")
        
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        elif guild.icon:
            embed.set_image(url=guild.icon.url)

        add_box_field(embed, "НЭГЖҮҮЛЭЛ", [
            f"╭ Эзэмшигч\n╰→ {guild.owner.mention} (`{guild.owner.name}`)",
            f"╭ Үүсгэсэн огноо\n╰→ {guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"╭ Серверийн ID\n╰→ {guild.id}",
        ])
        add_box_field(embed, "ГИШҮҮД", [
            f"╭ Жинхэнэ хүн\n╰→ {humans}",
            f"╭ Ботууд\n╰→ {bots}",
            f"╭ Нийт\n╰→ {total_members}",
        ])
        add_box_field(embed, "СУВГУУД", [
            f"╭ Текст сувгууд\n╰→ {text_channels}",
            f"╭ Дууны сувгууд\n╰→ {voice_channels}",
            f"╭ Категори\n╰→ {categories}",
        ])
        add_box_field(embed, "ҮҮРЭГ БА БУСТ", [
            f"╭ Роль\n╰→ {roles}",
            f"╭ Boost түвшин\n╰→ {boost_level} {'⭐' * boost_level if boost_level else '💨'}",
            f"╭ Boost тоо\n╰→ {boost_count}",
            f"╭ Баталгаажуулалт\n╰→ {verif_level}",
        ])
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='rolelist', description='Role жагсаалт харах')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def rolelist(self, interaction, member: discord.Member = None):
        ctx = SlashContext(interaction)
        await ctx.defer(ephemeral=False)
        if not ctx.guild:
            return
        roles = sorted([r for r in ctx.guild.roles if r.name != "@everyone"], key=lambda r: r.position, reverse=True)
        if not roles:
            embed = discord.Embed(title="🎭 **РОЛЬ БАЙХГҮЙ**", description="Энэ серверт @everyone-ээс өөр роль байхгүй.", color=WARNING_COLOR)
            return await ctx.send(embed=embed)
        embed = discord.Embed(title=f"🎭 **{ctx.guild.name} -ИЙН РОЛЬУУД**", description=f"Нийт **{len(roles)}** роль", color=EMBED_COLOR)
        chunks = [roles[i:i+10] for i in range(0, min(len(roles), 50), 10)]
        for idx, chunk in enumerate(chunks):
            value = ", ".join([r.mention for r in chunk])
            if len(value) > 1024:
                value = f"{len(chunk)} роль (жагсаалт хэт урт)"
            embed.add_field(name=f"📋 Роль бүлэг {idx+1}", value=value, inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='addmoney', description='Мөнгө нэмэх')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def addmoney(self, interaction, member: discord.Member, amount: int):
        ctx = SlashContext(interaction)
        if not self.is_owner_or_co_owner(ctx.author.id):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.ensure_user(member.id, ctx.guild.id)
        await economy.update_balance(member.id, ctx.guild.id, amount)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="✅ МӨНГӨ НЭМЭГДЛЭЭ", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө нэмлээ.", color=SUCCESS_COLOR)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2331/2331966.png")
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @app_commands.command(name='removemoney', description='Мөнгө хасах')
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def removemoney(self, interaction, member: discord.Member, amount: int):
        ctx = SlashContext(interaction)
        if not self.is_owner_or_co_owner(ctx.author.id):
            embed = discord.Embed(title="⛔ ЭРХ ХҮРЭХГҮЙ", description="Зөвхөн бот эзэмшигч / хамт эзэмшигч", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await ctx.defer(ephemeral=False)
        economy = self.bot.get_cog("Economy")
        if not economy:
            embed = discord.Embed(title="❌ АЛДАА", description="Эдийн засгийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        if amount <= 0:
            embed = discord.Embed(title="❌ АЛДАА", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        bal = await economy.get_balance(member.id, ctx.guild.id)
        if bal < amount:
            embed = discord.Embed(title="❌ ХАНГАЛТГҮЙ", description=f"{member.mention} -д **{amount:,}** мөнгө хасахад хангалтгүй.\n💰 Одоогийн үлдэгдэл: **{bal:,}** мөнгө", color=ERROR_COLOR)
            return await ctx.send(embed=embed)
        await economy.update_balance(member.id, ctx.guild.id, -amount)
        new_bal = await economy.get_balance(member.id, ctx.guild.id)
        embed = discord.Embed(title="⚠️ МӨНГӨ ХАСАГДЛАА", description=f"{ctx.author.mention} → {member.mention} **{amount:,}** мөнгө хаслаа.", color=WARNING_COLOR)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/190/190411.png")
        embed.add_field(name="💰 ШИНЭ ҮЛДЭГДЭЛ", value=f"```yaml\n{new_bal:,} мөнгө```", inline=False)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Admin(bot))
