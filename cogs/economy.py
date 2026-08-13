from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
from utils.branding import footer_text
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from utils.supabase_cog import SupabaseCog
import random
import time
import asyncio
import io
import os
import aiohttp
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont

# ---------- Centralized Unicode-aware font management ----------
from utils.fonts import load_font as _load_font

# ---------- Өнгөний палитр ----------
EMBED_COLOR   = 0x1e1e2f
SUCCESS_COLOR = 0x57f287
ERROR_COLOR   = 0xff0000
WARNING_COLOR = 0xfee75c
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
NEON_GREEN    = (57, 255, 20, 255)
NEON_YELLOW   = (204, 255, 0, 255)

STARTING_BALANCE = 5000
DAILY_MIN = 4000
DAILY_MAX = 15000

# ---------- Ажлын түвшин ----------
JOB_LEVELS = {
    1:  {"name":"Гудамжны цас цэвэрлэгч",           "min":1000,"max":3000,"emoji":"❄️"},
    5:  {"name":"Нарантуул дээр тэрэгчин",          "min":1500,"max":4200,"emoji":"🛒"},
    10: {"name":"CU / GS25-ын кассчин",             "min":2000,"max":4500,"emoji":"🏪"},
    15: {"name":"Хүргэлтийн курьер (Пицца)",        "min":2000,"max":4200,"emoji":"🍕"},
    20: {"name":"Фитнессийн зааварлагч",            "min":2800,"max":4400,"emoji":"💪"},
    25: {"name":"Компьютер форматлагч",             "min":3000,"max":5500,"emoji":"💻"},
    30: {"name":"График дизайнер (Freelancer)",      "min":3200,"max":4500,"emoji":"🎨"},
    40: {"name":"Сошиал контент бүтээгч",           "min":3500,"max":5600,"emoji":"📱"},
    50: {"name":"Маркетингийн менежер",             "min":4200,"max":5600,"emoji":"📊"},
    60: {"name":"Төслийн удирдагч",                 "min":4700,"max":6300,"emoji":"📋"},
    70: {"name":"Кибер аюулгүй байдлын мэргэжилтэн", "min":3300,"max":7800,"emoji":"🔒"},
    80: {"name":"Ахлах Программист",                "min":4600,"max":8700,"emoji":"⌨️"},
    90: {"name":"Алтны уурхайн инженер",             "min":3000,"max":9600,"emoji":"⛏️"},
    100:{"name":"Хувийн бизнес эрхлэгч",            "min":8000,"max":10000,"emoji":"🏢"},
    110:{"name":"Хөрөнгийн биржийн брокер",          "min":4400,"max":11200,"emoji":"📈"},
    120:{"name":"Томоохон банкны захирал",          "min":8500,"max":12300,"emoji":"🏦"},
    140:{"name":"Олон улсын нисгэгч",                "min":5600,"max":11300,"emoji":"✈️"},
    160:{"name":"Тэрбумтан хөрөнгө оруулагч",       "min":6400,"max":12700,"emoji":"💼"},
    180:{"name":"Сансрын нисгэгч",                   "min":5800,"max":14500,"emoji":"🚀"},
    200:{"name":"Дэлхийн Эзэн",                     "min":6000,"max":18000,"emoji":"🌍"},
}

# ---------- Гэмт хэрэг ----------
CRIMES = [
    {"name":"Банкны ATM дээрэмдэх","success_chance":0.45,"min_reward":5000,"max_reward":15000},
    {"name":"Машин хулгайлах","success_chance":0.35,"min_reward":8000,"max_reward":20000},
    {"name":"Хүн дээрэмдэх","success_chance":0.55,"min_reward":2000,"max_reward":8000},
    {"name":"Дэлгүүр тонож байна","success_chance":0.50,"min_reward":4000,"max_reward":12000},
    {"name":"Хакердах","success_chance":0.25,"min_reward":10000,"max_reward":25000},
    {"name":"Гэмт бүлэгт элсэх","success_chance":0.15,"min_reward":1500,"max_reward":5000},
]

def _fmt_money(n: int) -> str:
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B ₮"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M ₮"
    return f"{n:,} ₮"

# ================== MAIN ECONOMY COG ==================
class Economy(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.max_balance = bot.config.get("max_balance", 100_000_000)
        self.transfer_tax_percent = bot.config.get("transfer_tax_percent", 10)
        self.bonus_percent = bot.config.get("bonus_percent", 10)
        self.chat_money_cooldown = {}
        self.use_default_replies = True

    async def cog_load(self):
        # Tables are pre-configured in Supabase
        self.role_income_task = self.bot.loop.create_task(self._role_income_loop())

    async def ensure_user(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        if not row:
            await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid)})

    async def get_balance(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row.get("balance", 0) if row else 0

    async def update_balance(self, uid, gid, delta):
        await self.ensure_user(uid, gid)
        cur = await self.get_balance(uid, gid)
        new = max(0, min(self.max_balance, cur + delta))
        await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid), "balance": new})
        return new

    async def get_bank(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row.get("bank_balance", 0) if row else 0

    async def update_bank(self, uid, gid, delta):
        await self.ensure_user(uid, gid)
        cur = await self.get_bank(uid, gid)
        new = max(0, min(self.max_balance, cur + delta))
        await self.update_data("economy", {"user_id": str(uid), "guild_id": str(gid), "bank_balance": new})
        return new

    # ------- USER MANAGEMENT -------
    async def check_registration(self, ctx):
        await self.ensure_user(ctx.author.id, ctx.guild.id)
        return True

    # ------- HUNGER / MOOD -------
    async def get_hunger_mood(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return (row.get("hunger", 0), row.get("mood", 0)) if row else (0, 0)

    async def set_hunger_mood(self, uid, gid, hunger=None, mood=None):
        updates = {}
        if hunger is not None:
            updates["hunger"] = max(0, min(100, hunger))
        if mood is not None:
            updates["mood"] = max(0, min(100, mood))
        if updates:
            await self.bot.db_manager.update(
                "economy", {"user_id": str(uid), "guild_id": str(gid)}, updates
            )

    # ------- LEVEL / JOB -------
    async def get_discord_level(self, uid, gid):
        level_cog = self.bot.get_cog("Leveling")
        if level_cog:
            row = await self.get_data("levels", {"user_id": str(uid), "guild_id": str(gid)})
            if row:
                return row.get("level", 1)
        return 1

    def get_job_for_level(self, lvl):
        for req in sorted(JOB_LEVELS.keys(), reverse=True):
            if lvl >= req:
                return req, JOB_LEVELS[req]
        return 1, JOB_LEVELS[1]

    # ------- PRISON / BANK PROTECTION -------
    async def is_in_prison(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        return row and row.get("prison_until") and row["prison_until"] > int(time.time())

    async def set_prison(self, uid, gid, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db_manager.update(
            "economy", {"user_id": str(uid), "guild_id": str(gid)}, {"prison_until": until}
        )

    async def set_bank_protection(self, uid, gid, hours=2):
        until = int(time.time()) + (hours * 3600)
        await self.bot.db_manager.update(
            "economy", {"user_id": str(uid), "guild_id": str(gid)}, {"bank_protect_until": until}
        )

    async def get_bank_protection_remaining(self, uid, gid):
        row = await self.get_data("economy", {"user_id": str(uid), "guild_id": str(gid)})
        if row and row.get("bank_protect_until") and row["bank_protect_until"] > int(time.time()):
            return row["bank_protect_until"] - int(time.time())
        return 0

    async def is_bank_protected(self, uid, gid):
        return await self.get_bank_protection_remaining(uid, gid) > 0

    # ------- ADMIN CONFIG SETTERS -------
    async def set_cooldown_cmd(self, interaction, command, seconds):
        await self.bot.db_manager.upsert(
            "economy_cooldowns_config",
            {"guild_id": str(interaction.guild_id), "command": command, "cooldown_seconds": seconds},
            on_conflict="guild_id,command",
        )

    async def set_fine_amount(self, interaction, command, mn, mx):
        await self.bot.db_manager.upsert(
            "economy_fines_config",
            {"guild_id": str(interaction.guild_id), "command": command, "fine_min": mn, "fine_max": mx},
            on_conflict="guild_id,command",
        )

    async def set_payout(self, interaction, command, mn, mx):
        await self.bot.db_manager.upsert(
            "economy_payouts_config",
            {"guild_id": str(interaction.guild_id), "command": command, "payout_min": mn, "payout_max": mx},
            on_conflict="guild_id,command",
        )

    async def set_fail_rate(self, interaction, command, rate):
        await self.bot.db_manager.upsert(
            "economy_fail_rates",
            {"guild_id": str(interaction.guild_id), "command": command, "fail_rate": rate},
            on_conflict="guild_id,command",
        )

    async def add_reply(self, interaction, command, text, rtype):
        await self.bot.db_manager.insert(
            "custom_replies",
            {"guild_id": str(interaction.guild_id), "command": command, "type": rtype, "text": text},
        )

    # ================== COMMANDS ==================
    @commands.command(name='admin-panel')
    @commands.has_permissions(administrator=True)
    async def admin_panel(self, ctx):
        embed = discord.Embed(title="🛠️ **Админ Тохиргооны Самбар**",
                              description="Товчлуураар тохиргоог хийх боломжтой.", color=INFO_COLOR)
        view = AdminPanelView(self, ctx)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='workphrase', description='Ажлын өгүүлбэрийн тохиргоо (embed+button+modal)')
    @commands.has_permissions(administrator=True)
    async def work_phrase_panel(self, ctx):
        embed = discord.Embed(
            title="📝 Ажлын өгүүлбэрийн тохиргоо",
            description="Доорх товчлуураар өгүүлбэр нэмэх, хасах, жагсаалт харах эсвэл бүгдийг устгах боломжтой.",
            color=GOLD_COLOR
        )
        embed.set_footer(text="Зөвхөн админ ашиглах боломжтой")
        view = WorkPhraseView(self, ctx)
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=['bal','money','wallet','bank'])
    async def balance(self, ctx, member: discord.Member = None):
        if not await self.check_registration(ctx): return
        target = member or ctx.author
        cash = await self.get_balance(target.id, ctx.guild.id)
        bank = await self.get_bank(target.id, ctx.guild.id)
        total = cash + bank
        disc_level = await self.get_discord_level(target.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)
        embed = discord.Embed(title=f"🏦 {target.display_name} - САНХҮҮ",
                              color=0xffd700 if total >= 50000 else 0x2b2d31)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="💰 Гар дээр", value=f"**{cash:,}** ₮", inline=True)
        embed.add_field(name="🏦 Банканд", value=f"**{bank:,}** ₮", inline=True)
        embed.add_field(name="💎 Нийт хөрөнгө", value=f"**{total:,}** ₮", inline=False)
        embed.add_field(name="💼 Ажил", value=f"{job['emoji']} **{job['name']}** (Түв.{job_level})", inline=True)
        embed.add_field(name="⭐ Discord Түвшин", value=f"**{disc_level}**", inline=True)
        embed.set_footer(text=footer_text(ctx.author.name), icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='work')
    async def work(self, ctx, *, custom_text: str = None):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос ажиллах боломжгүй.", color=ERROR_COLOR))
        hunger, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger >= 80:
            return await ctx.send(embed=discord.Embed(title="🍔 Өлсөж байна!", description="`eat` командаар хоол идээрэй.", color=WARNING_COLOR))
        if mood >= 80:
            return await ctx.send(embed=discord.Embed(title="😡 Ууртай байна!", description="`relax` командаар амраарай.", color=WARNING_COLOR))
        now = int(time.time())
        row = await self.bot.db_manager.fetch_one("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, selects="last_work")
        last = row.get("last_work", 0) if row else 0
        if last and now - last < 1800:
            rem = 1800 - (now-last)
            m, s = divmod(rem, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ АМРАЛТ", description=f"**{m}м {s}с** хүлээ.", color=WARNING_COLOR))

        disc_level = await self.get_discord_level(ctx.author.id, ctx.guild.id)
        job_level, job = self.get_job_for_level(disc_level)
        pay = random.randint(job["min"], job["max"])
        bonus = min(50, disc_level * 2)
        if bonus: pay = int(pay * (1 + bonus/100))

        if custom_text:
            work_desc = custom_text
        else:
            rows = await self.bot.db_manager.fetch_all("work_phrases", {"guild_id": str(ctx.guild.id)}, selects="phrase")
            if rows:
                work_desc = random.choice(rows)["phrase"]
            else:
                work_desc = f"{job['emoji']} {job['name']} ажил"

        await self.update_balance(ctx.author.id, ctx.guild.id, pay)
        hunger_inc = random.randint(15, 25)
        mood_inc = random.randint(10, 20)
        new_hunger = min(100, hunger+hunger_inc)
        new_mood = min(100, mood+mood_inc)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger, mood=new_mood)
        await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"last_work": now})
        leveling = self.bot.get_cog("Leveling")
        if leveling:
            try:
                await leveling.add_xp(ctx.author.id, ctx.guild.id, random.randint(10, 20), member=ctx.author, check_mute=True, channel=ctx.channel)
            except: pass

        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "economy_work", 1)

        embed = discord.Embed(
            title="💼 АЖИЛ АМЖИЛТТАЙ!",
            description=f"{ctx.author.mention} **{work_desc}** хийж, **{pay:,}** ₮ оллоо!\n⭐ Урамшуулал: +{bonus}%",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="💰 Цалин", value=f"+ {pay:,} ₮", inline=True)
        embed.add_field(name="🍔 Өлсгөлөн", value=f"+{hunger_inc}% (одоо {new_hunger}/100)", inline=True)
        embed.add_field(name="😡 Уур", value=f"+{mood_inc}% (одоо {new_mood}/100)", inline=True)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Дараагийн ажил 30 минутын дараа")
        await ctx.send(embed=embed)

    @commands.command(name='daily')
    async def daily(self, ctx):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос урамшуулал авах боломжгүй.", color=ERROR_COLOR))
        now = int(time.time())
        row = await self.bot.db_manager.fetch_one("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, selects="last_daily")
        last = row.get("last_daily", 0) if row else 0
        if last and now - last < 86400:
            rem = 86400 - (now-last)
            h, m, s = rem//3600, (rem%3600)//60, rem%60
            return await ctx.send(embed=discord.Embed(title="⏰ ӨДРИЙН УРАМШУУЛАЛ АВСАН", description=f"Дараагийн урамшуулал {h}ц {m}м {s}с дараа", color=WARNING_COLOR))
        reward = random.randint(DAILY_MIN, DAILY_MAX)
        await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"last_daily": now})
        await self.update_balance(ctx.author.id, ctx.guild.id, reward)
        leveling = self.bot.get_cog("Leveling")
        if leveling:
            try: await leveling.add_xp(ctx.author.id, ctx.guild.id, random.randint(5, 10), member=ctx.author, check_mute=True, channel=ctx.channel)
            except: pass
        embed = discord.Embed(
            title="🎉 ӨДРИЙН УРАМШУУЛАЛ!",
            description=f"{ctx.author.mention} та өнөөдрийн урамшуулал авлаа.",
            color=SUCCESS_COLOR,
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="💰 Шагнал", value=f"+ **{reward:,}** ₮")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Дараагийн урамшуулал 24 цагийн дараа")
        await ctx.send(embed=embed)

    @commands.command(name='crime')
    async def crime(self, ctx):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронд гэмт хэрэг үйлдэх боломжгүй.", color=ERROR_COLOR))
        crime = random.choice(CRIMES)
        if random.random() < crime["success_chance"]:
            reward = random.randint(crime["min_reward"], crime["max_reward"])
            await self.update_balance(ctx.author.id, ctx.guild.id, reward)
            leveling = self.bot.get_cog("Leveling")
            if leveling: await leveling.add_xp(ctx.author.id, ctx.guild.id, random.randint(10, 20), member=ctx.author, check_mute=True, channel=ctx.channel)
            embed = discord.Embed(title="🎉 ГЭМТ ХЭРЭГ АМЖИЛТТАЙ!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэж, **{reward:,}** ₮ оллоо!",
                                  color=SUCCESS_COLOR,
                                  timestamp=datetime.now(timezone.utc))
            embed.add_field(name="💰 Шагнал", value=f"+ {reward:,} ₮")
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)
        else:
            jail_time = random.randint(1, 3)
            await self.set_prison(ctx.author.id, ctx.guild.id, hours=jail_time)
            embed = discord.Embed(title="🚔 ТА ЦАГДААД БАРИГДЛАА!",
                                  description=f"{ctx.author.mention} **{crime['name']}** үйлдэх гэж оролдсон боловч баригдлаа! {jail_time} цаг шоронд сууна.",
                                  color=ERROR_COLOR,
                                  timestamp=datetime.now(timezone.utc))
            embed.set_thumbnail(url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

    @commands.command(name='transfer', aliases=['send', 'give'])
    async def transfer(self, ctx, member: discord.Member, amount_str: str):
        if not await self.check_registration(ctx): return
        if await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронгоос мөнгө шилжүүлэх боломжгүй.", color=ERROR_COLOR))
        if amount_str.lower() == 'all':
            amount = await self.get_balance(ctx.author.id, ctx.guild.id)
        else:
            try: amount = int(amount_str)
            except: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amount <= 0: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн эерэг байх ёстой.", color=ERROR_COLOR))
        if member.id == ctx.author.id: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Өөртөө мөнгө шилжүүлэх боломжгүй.", color=ERROR_COLOR))
        tax = int(amount * self.transfer_tax_percent / 100)
        final_amount = amount - tax
        if final_amount <= 0: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Татварын дараа шилжих мөнгө 0 боллоо.", color=ERROR_COLOR))
        sender_bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if sender_bal < amount: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description=f"Танд {amount:,} ₮ хүрэлцэхгүй.", color=ERROR_COLOR))
        embed = discord.Embed(title="💰 МӨНГӨ ШИЛЖҮҮЛЭХ",
                              description=f"{ctx.author.mention} → {member.mention}\nДүн: **{amount:,}** ₮\nТатвар ({self.transfer_tax_percent}%): **{tax:,}** ₮\nХүлээн авах дүн: **{final_amount:,}** ₮",
                              color=GOLD_COLOR)
        view = ConfirmView()
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()
        if view.value is not True:
            return await ctx.send("❌ Шилжүүлэг цуцлагдлаа.", ephemeral=True)
        await self.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await self.update_balance(member.id, ctx.guild.id, final_amount)
        success_embed = discord.Embed(title="✅ ГҮЙЛГЭЭ АМЖИЛТТАЙ!",
                                      description=f"{ctx.author.mention} → {member.mention} **{amount:,}** ₮ шилжүүллээ.",
                                      color=SUCCESS_COLOR)
        await ctx.send(embed=success_embed)
        try: await member.send(f"📨 {ctx.author.display_name} танд **{final_amount:,}** ₮ шилжүүллээ!")
        except: pass

    @commands.command(name='deposit', aliases=['dep'])
    async def deposit(self, ctx, amount_str: str):
        if not await self.check_registration(ctx): return
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all': amt = cash
        else:
            try: amt = int(amount_str)
            except: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amt <= 0 or cash < amt:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн буруу эсвэл мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if bank + amt > self.max_balance:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Банкны хязгаарт хүрнэ.", color=ERROR_COLOR))
        await self.update_balance(ctx.author.id, ctx.guild.id, -amt)
        await self.update_bank(ctx.author.id, ctx.guild.id, amt)
        new_bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(title="🏦 БАНКАНД ХАДГАЛАВ",
                              description=f"{ctx.author.mention} **{amt:,}** ₮ хадгаллаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.add_field(name="💰 Шинэ банкны үлдэгдэл", value=f"**{new_bank:,}** ₮")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='withdraw', aliases=['with'])
    async def withdraw(self, ctx, amount_str: str):
        if not await self.check_registration(ctx): return
        bank = await self.get_bank(ctx.author.id, ctx.guild.id)
        if amount_str.lower() == 'all': amt = bank
        else:
            try: amt = int(amount_str)
            except: return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн нь тоо эсвэл 'all' байх ёстой.", color=ERROR_COLOR))
        if amt <= 0 or bank < amt:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн буруу эсвэл банканд мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        if cash + amt > self.max_balance:
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Гар дээрх хязгаарт хүрнэ.", color=ERROR_COLOR))
        await self.update_bank(ctx.author.id, ctx.guild.id, -amt)
        await self.update_balance(ctx.author.id, ctx.guild.id, amt)
        new_cash = await self.get_balance(ctx.author.id, ctx.guild.id)
        embed = discord.Embed(title="🏦 БАНКНААС АВЛАА",
                              description=f"{ctx.author.mention} **{amt:,}** ₮ авлаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.add_field(name="💰 Шинэ гар дээрх үлдэгдэл", value=f"**{new_cash:,}** ₮")
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='eat')
    async def eat(self, ctx):
        if not await self.check_registration(ctx): return
        bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        cost = 3000
        if bal < cost: return await ctx.send(embed=discord.Embed(title="❌ Мөнгө хүрэлцэхгүй", description=f"Хоолны үнэ {cost:,} ₮.", color=ERROR_COLOR))
        hunger, _ = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger == 0: return await ctx.send(embed=discord.Embed(title="🍔 Цадсан", description="Та аль хэдийн цадсан байна!", color=WARNING_COLOR))
        await self.update_balance(ctx.author.id, ctx.guild.id, -cost)
        new_hunger = max(0, hunger-50)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger)
        embed = discord.Embed(title="🍔 ХООЛ ИДЭВ",
                              description=f"Өлсгөлөн **{hunger}** → **{new_hunger}**",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='relax')
    async def relax(self, ctx):
        if not await self.check_registration(ctx): return
        _, mood = await self.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if mood == 0: return await ctx.send(embed=discord.Embed(title="🧘 Тайван", description="Та аль хэдийн тайван байна!", color=WARNING_COLOR))
        new_mood = max(0, mood-40)
        await self.set_hunger_mood(ctx.author.id, ctx.guild.id, mood=new_mood)
        embed = discord.Embed(title="🧘 АМРАВ",
                              description=f"Уур бухимдал **{mood}** → **{new_mood}**",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='bankprotect', aliases=['bp', 'block'])
    async def bank_protect(self, ctx):
        if not await self.check_registration(ctx): return
        rem = await self.get_bank_protection_remaining(ctx.author.id, ctx.guild.id)
        if rem > 0:
            hours, minutes = rem//3600, (rem%3600)//60
            return await ctx.send(embed=discord.Embed(title="🛡️ БАНК ХАМГААЛАГДСАН", description=f"Үлдсэн: {hours}ц {minutes}м", color=WARNING_COLOR))
        await self.set_bank_protection(ctx.author.id, ctx.guild.id, hours=2)
        embed = discord.Embed(title="🛡️ БАНК АМЖИЛТТАЙ ХАМГААЛАГДЛАА",
                              description="2 цагийн турш хулгай, татвараас хамгаалагдлаа!",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name='bail', aliases=['шоронгоосгарах', 'bailout'])
    async def bail(self, ctx):
        if not await self.check_registration(ctx): return
        if not await self.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="❌ АЛДАА", description="Та шоронд байхгүй байна!", color=ERROR_COLOR))
        fine = 5000
        bal = await self.get_balance(ctx.author.id, ctx.guild.id)
        if bal < fine:
            return await ctx.send(embed=discord.Embed(
                title="❌ МӨНГӨ ХҮРЭЛЦЭХГҮЙ",
                description=f"Таны гар дээр {fine:,}₮ байхгүй байна. Одоогийн үлдэгдэл: {bal:,}₮",
                color=ERROR_COLOR
            ))
        await self.update_balance(ctx.author.id, ctx.guild.id, -fine)
        await self.bot.db_manager.update("economy", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}, {"prison_until": 0})
        embed = discord.Embed(title="🕊️ ШОРОНГООС ГАРЛАА",
                              description=f"{ctx.author.mention} та **{fine:,}₮** төлж шоронгоос гарлаа.",
                              color=SUCCESS_COLOR,
                              timestamp=datetime.now(timezone.utc))
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)

    async def _role_income_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                rows = await self.bot.db_manager.fetch_all("role_income")
                for r in rows:
                    guild_id, role_id, amount, interval = r["guild_id"], r["role_id"], r["amount"], r["interval_seconds"]
                    guild = self.bot.get_guild(int(guild_id))
                    if not guild: continue
                    role = guild.get_role(int(role_id))
                    if not role: continue
                    for member in role.members:
                        if not member.bot:
                            await self.update_balance(member.id, guild.id, amount)
            except Exception:
                pass
            await asyncio.sleep(60)

# ---------- VIEWS & MODALS ----------
class ConfirmView(View):
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None
    @discord.ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: Button):
        self.value = True
        self.stop()
        await interaction.response.defer()
    @discord.ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        self.value = False
        self.stop()
        await interaction.response.defer()

class AdminPanelView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=180)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(label="⏱ Cooldown", style=discord.ButtonStyle.grey)
    async def cooldown_btn(self, interaction: discord.Interaction, button: Button):
        modal = CooldownModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💸 Торгууль", style=discord.ButtonStyle.grey)
    async def fine_btn(self, interaction: discord.Interaction, button: Button):
        modal = FineModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💰 Цалин (Payout)", style=discord.ButtonStyle.grey)
    async def payout_btn(self, interaction: discord.Interaction, button: Button):
        modal = PayoutModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎲 Бүтэлгүйтэх %", style=discord.ButtonStyle.grey)
    async def failrate_btn(self, interaction: discord.Interaction, button: Button):
        modal = FailRateModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="💬 Custom Reply", style=discord.ButtonStyle.blurple)
    async def reply_btn(self, interaction: discord.Interaction, button: Button):
        modal = CustomReplyModal()
        await interaction.response.send_modal(modal)

class CooldownModal(Modal, title="Cooldown тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="work", required=True)
    seconds = TextInput(label="Cooldown (секунд)", placeholder="3600", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        cmd = self.command.value.lower()
        sec = int(self.seconds.value)
        await cog.set_cooldown_cmd(interaction, cmd, sec)
        await interaction.response.send_message(f"✅ `{cmd}` cooldown {sec}с боллоо.", ephemeral=True)

class FineModal(Modal, title="Торгууль тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="rob")
    fine_min = TextInput(label="Min торгууль", placeholder="100")
    fine_max = TextInput(label="Max торгууль", placeholder="500")
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        cmd = self.command.value.lower()
        mn = int(self.fine_min.value)
        mx = int(self.fine_max.value)
        await cog.set_fine_amount(interaction, cmd, mn, mx)
        await interaction.response.send_message(f"✅ `{cmd}` торгууль {mn}-{mx} боллоо.", ephemeral=True)

class PayoutModal(Modal, title="Цалин тохируулах"):
    command = TextInput(label="Командын нэр", placeholder="work")
    payout_min = TextInput(label="Min цалин")
    payout_max = TextInput(label="Max цалин")
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        cmd = self.command.value.lower()
        mn = int(self.payout_min.value)
        mx = int(self.payout_max.value)
        await cog.set_payout(interaction, cmd, mn, mx)
        await interaction.response.send_message(f"✅ `{cmd}` цалин {mn}-{mx} боллоо.", ephemeral=True)

class FailRateModal(Modal, title="Бүтэлгүйтэх магадлал"):
    command = TextInput(label="Командын нэр")
    rate = TextInput(label="Магадлал (0-1)", placeholder="0.5")
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        cmd = self.command.value.lower()
        r = float(self.rate.value)
        await cog.set_fail_rate(interaction, cmd, r)
        await interaction.response.send_message(f"✅ `{cmd}` бүтэлгүйтэх {r*100}% боллоо.", ephemeral=True)

class CustomReplyModal(Modal, title="Custom Reply нэмэх"):
    command = TextInput(label="Команд")
    reply_type = TextInput(label="Төрөл (success/fail)")
    text = TextInput(label="Текст", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Economy")
        await cog.add_reply(interaction, self.command.value, self.text.value, self.reply_type.value)
        await interaction.response.send_message("✅ Custom reply нэмэгдлээ.", ephemeral=True)

class WorkPhraseView(View):
    def __init__(self, cog, ctx):
        super().__init__(timeout=300)
        self.cog = cog
        self.ctx = ctx

    @discord.ui.button(label="➕ Нэмэх", style=discord.ButtonStyle.green)
    async def add_phrase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AddPhraseModal(self.cog, interaction.guild_id))

    @discord.ui.button(label="➖ Хасах", style=discord.ButtonStyle.red)
    async def remove_phrase(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RemovePhraseModal(self.cog, interaction.guild_id))

    @discord.ui.button(label="📋 Жагсаалт", style=discord.ButtonStyle.blurple)
    async def list_phrases(self, interaction: discord.Interaction, button: Button):
        rows = await self.cog.bot.db_manager.fetch_all("work_phrases", {"guild_id": str(interaction.guild_id)}, selects="id,phrase")
        if not rows:
            embed = discord.Embed(title="📋 Ажлын өгүүлбэрүүд", description="Хоосон", color=WARNING_COLOR)
        else:
            embed = discord.Embed(title="📋 Ажлын өгүүлбэрүүд", color=INFO_COLOR)
            for r in rows[:20]:
                embed.add_field(name=f"ID {r['id']}", value=r['phrase'], inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🧹 Бүгдийг устгах", style=discord.ButtonStyle.gray)
    async def clear_phrases(self, interaction: discord.Interaction, button: Button):
        await self.cog.bot.db_manager.delete("work_phrases", {"guild_id": str(interaction.guild_id)})
        await interaction.response.send_message("✅ Бүх өгүүлбэр устгагдлаа.", ephemeral=True)

class AddPhraseModal(Modal, title="Ажлын өгүүлбэр нэмэх"):
    phrase = TextInput(label="Өгүүлбэр (хамгийн ихдээ 160 тэмдэгт)", placeholder="Жишээ: Кофе чанаж байна", max_length=160, required=True)
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
    async def on_submit(self, interaction: discord.Interaction):
        if len(self.phrase.value) > 160:
            return await interaction.response.send_message("❌ 160 тэмдэгтээс хэтрэхгүй байх ёстой.", ephemeral=True)
        await self.cog.bot.db_manager.insert("work_phrases", {"guild_id": str(self.guild_id), "phrase": self.phrase.value})
        await interaction.response.send_message(f"✅ Өгүүлбэр нэмэгдлээ: {self.phrase.value}", ephemeral=True)

class RemovePhraseModal(Modal, title="Өгүүлбэр хасах"):
    phrase_id = TextInput(label="ID дугаар", placeholder="Устгах өгүүлбэрийн ID", required=True)
    def __init__(self, cog, guild_id):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
    async def on_submit(self, interaction: discord.Interaction):
        try:
            pid = int(self.phrase_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ ID нь тоо байх ёстой.", ephemeral=True)
        await self.cog.bot.db_manager.delete("work_phrases", {"guild_id": str(self.guild_id), "id": pid})
        await interaction.response.send_message(f"✅ {pid} ID-тай өгүүлбэр устгагдлаа.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Economy(bot))