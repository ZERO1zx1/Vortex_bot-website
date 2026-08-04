import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import time
import platform
import psutil

from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_time = time.time()

    def is_owner_or_co_owner(self, user_id):
        return user_id in self.bot.owner_ids

    @commands.hybrid_command(name='status', description='Check bot status and health', with_app_command=True)
    async def status(self, ctx):
        await ctx.defer()
        uptime = str(datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"))
        latency = round(self.bot.latency * 1000)
        cpu_usage = psutil.cpu_percent()
        ram_usage = psutil.virtual_memory().percent
        
        embed = discord.Embed(title="🤖 Бот-ын төлөв", color=INFO_COLOR)
        embed.add_field(name="⏳ Ажилласан хугацаа", value=f"`{uptime}`", inline=True)
        embed.add_field(name="📡 Хоцролт", value=f"`{latency}ms`", inline=True)
        embed.add_field(name="💻 CPU", value=f"`{cpu_usage}%`", inline=True)
        embed.add_field(name="🧠 RAM", value=f"`{ram_usage}%`", inline=True)
        embed.add_field(name="⚙️ Систем", value=f"`{platform.system()}`", inline=True)
        embed.add_field(name="🐍 Python", value=f"`{platform.python_version()}`", inline=True)
        
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='info', description='Серверийн мэдээлэл харах', aliases=['serverinfo'], with_app_command=True)
    async def info(self, ctx):
        await ctx.defer(ephemeral=False)
        if ctx.guild is None:
            embed = discord.Embed(title="❌ АЛДАА", description="Зөвхөн сервер дотор ашиглах боломжтой.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

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

        embed = discord.Embed(
            title=f"📌 **{guild.name}**",
            description="*Серверийн дэлгэрэнгүй мэдээлэл*",
            color=GOLD_COLOR if guild.premium_tier > 0 else EMBED_COLOR,
            timestamp=datetime.now()
        )

        if guild.banner:
            embed.set_image(url=guild.banner.url)
        elif guild.icon:
            embed.set_image(url=guild.icon.url)

        embed.add_field(name="👑 **Эзэмшигч**", value=f"{guild.owner.mention}\n`{guild.owner.name}`", inline=True)
        embed.add_field(name="📅 **Үүсгэсэн**", value=f"`{guild.created_at.strftime('%Y-%m-%d %H:%M:%S')}`", inline=True)
        embed.add_field(name="🆔 **Серверийн ID**", value=f"`{guild.id}`", inline=True)
        embed.add_field(name="👥 **Гишүүд**", value=f"👨 Жинхэнэ: `{humans}`\n🤖 Бот: `{bots}`\n📊 Нийт: `{total_members}`", inline=True)
        embed.add_field(name="💬 **Сувгууд**", value=f"📝 Текст: `{text_channels}`\n🎙️ Дууны: `{voice_channels}`\n📁 Категори: `{categories}`", inline=True)
        embed.add_field(name="🎭 **Роль**", value=f"`{roles}` роль", inline=True)
        boost_emoji = "⭐" if boost_level == 1 else "🌟🌟" if boost_level == 2 else "🌟🌟🌟" if boost_level == 3 else "💨"
        embed.add_field(name="🚀 **Boost**", value=f"{boost_emoji} Түвшин: `{boost_level}`\n⚡ Boost: `{boost_count}`", inline=True)
        embed.add_field(name="🔐 **Баталгаажуулалт**", value=verif_level, inline=True)
        embed.set_footer(text=f"Хүсэлт гаргасан: {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name='rolelist', description='Role жагсаалт харах', aliases=['roles'], with_app_command=True)
    @commands.has_permissions(administrator=True)
    @app_commands.default_permissions(administrator=True)
    async def rolelist(self, ctx, member: discord.Member = None):
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

    @commands.hybrid_command(name='addmoney', description='Мөнгө нэмэх', aliases=['am'], with_app_command=True)
    async def addmoney(self, ctx, member: discord.Member, amount: int):
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

    @commands.hybrid_command(name='removemoney', description='Мөнгө хасах', aliases=['rm'], with_app_command=True)
    async def removemoney(self, ctx, member: discord.Member, amount: int):
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
