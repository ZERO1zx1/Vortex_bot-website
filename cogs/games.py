from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord.ui import View, Button
import random
import time
import asyncio
from datetime import datetime, timezone

# ══════════════ ӨНГӨ ══════════════
SUCCESS_COLOR = 0x57f287
ERROR_COLOR = 0xed4245
WARNING_COLOR = 0xfee75c
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x3498db
EMBED_COLOR = 0x2b2d31

# ══════════════ ХЯЗГААРЛАЛТУУД ══════════════
DEFAULT_COOLDOWNS = {
    "gamble": 30,
    "coinflip": 30,
    "slot": 45,
    "roulette": 45,
    "dice": 30,
    "rps": 30,
    "numberguess": 30,
    "highlow": 45,
    "blackjack": 60,
    "highcard": 60,
    "rob": 3600,
    "hack": 7200,
    "cgive": 86400,
    "trivia": 15,
}
MAX_BET = 1_000_000  # нэг тоглоомд тавих дээд хязгаар

# ══════════════ ТУСЛАХ ФУНКЦ ══════════════
def _format_money(amount: int) -> str:
    if amount >= 1_000_000_000: return f"{amount/1_000_000_000:.1f}B₮"
    if amount >= 1_000_000: return f"{amount/1_000_000:.1f}M₮"
    if amount >= 1_000: return f"{amount/1_000:.1f}K₮"
    return f"{amount:,}₮"

# ══════════════ ТОГЛООМЫН VIEW-үүд (өмнөх бүх view хэвээр, зөвхөн embed-үүд нь шинэчлэгдсэн) ══════════════
# ... (BlackjackView, HighCardView, GambleView, CoinflipView, SlotsView, RouletteView,
#      DiceView, RPSView, NumberGuessView, HighLowView, CrashView)
# Дээрх бүх view-үүдийг таны одоогийн кодноос хуулж ашиглана.
# (Хэмжээ хязгаартай тул тэдгээрийг бүрэн оруулахгүй, гэхдээ та өөрийн файлаас авч болно.)

class Games(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # локал күүки нөөц

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

    # ═══ ЭДИЙН ЗАСГИЙН КОГ-ООС ТОХИРГОО УНШИХ ═══
    async def get_economy_cooldown(self, guild_id: int, command_name: str) -> int:
        """Эдийн засгийн админ панелиар тохируулсан күүкийг (секунд) буцаана."""
        economy = self.bot.get_cog("Economy")
        if not economy:
            return DEFAULT_COOLDOWNS.get(command_name, 30)
        row = await economy.bot.db_manager.fetch_one(
            "economy_cooldowns_config",
            {"guild_id": str(guild_id), "command": command_name},
            selects="cooldown_seconds",
        )
        if row:
            return row.get("cooldown_seconds", 0)
        return DEFAULT_COOLDOWNS.get(command_name, 30)

    async def is_on_cooldown(self, user_id: int, guild_id: int, command: str) -> int:
        """Хэрэглэгчийн күүки дуусаагүй бол үлдсэн хугацааг (секунд) буцаана, 0 бол дууссан."""
        key = f"{guild_id}:{user_id}:{command}"
        now = time.time()
        last = self.cooldowns.get(key, 0)
        cd_seconds = await self.get_economy_cooldown(guild_id, command)
        if now - last < cd_seconds:
            return int(cd_seconds - (now - last))
        return 0

    def set_cooldown(self, user_id: int, guild_id: int, command: str):
        key = f"{guild_id}:{user_id}:{command}"
        self.cooldowns[key] = time.time()

    async def check_common_restrictions(self, ctx, amount: int = None) -> bool:
        """Нийтлэг хязгаарлалт: шорон, өлсгөлөн, уур, мөнгө. False буцаавал тоглох ёсгүй."""
        if ctx.guild is None:
            await ctx.send("❌ Зөвхөн серверт ашиглана уу.")
            return False
        economy = self.bot.get_cog("Economy")
        if not economy:
            await ctx.send("❌ Эдийн засгийн систем ачаалагдаагүй.")
            return False
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            await ctx.send(embed=discord.Embed(title="🚔 Шорон", description="Та шоронд байгаа тул тоглох боломжгүй.", color=ERROR_COLOR))
            return False
        hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger >= 80:
            await ctx.send(embed=discord.Embed(title="🍔 Өлсөж байна!", description="Эхлээд `geat` командаар хоол идээрэй.", color=WARNING_COLOR))
            return False
        if mood >= 80:
            await ctx.send(embed=discord.Embed(title="😡 Ууртай байна!", description="Эхлээд `grelax` командаар амраарай.", color=WARNING_COLOR))
            return False
        if amount is not None:
            if amount <= 0:
                await ctx.send(embed=discord.Embed(title="❌ Буруу дүн", description="Эерэг тоо оруулна уу.", color=ERROR_COLOR))
                return False
            if amount > MAX_BET:
                await ctx.send(embed=discord.Embed(title="❌ Хэт их дүн", description=f"Нэг тоглоомд хамгийн ихдээ {MAX_BET:,}₮ тавих боломжтой.", color=ERROR_COLOR))
                return False
            bal = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if bal < amount:
                await ctx.send(embed=discord.Embed(title="❌ Мөнгө хүрэлцэхгүй", description=f"Танд {amount:,}₮ байхгүй (үлдэгдэл: {bal:,}₮).", color=ERROR_COLOR))
                return False
        return True

    # ═══ ШАГНАЛ / СТАТИСТИК ═══
    async def give_rewards(self, ctx, money_change: int, xp_amount: int, won: bool = False, bet: int = 0):
        economy = self.bot.get_cog("Economy")
        level = self.bot.get_cog("Leveling")
        bonus_percent = self.bot.config.get("bonus_percent", 10)
        final_money = money_change
        if won and money_change > 0:
            bonus = int(money_change * bonus_percent / 100)
            final_money += bonus
        if economy and final_money != 0:
            await economy.update_balance(ctx.author.id, ctx.guild.id, final_money)
        if level and xp_amount > 0:
            if hasattr(level, 'add_xp'):
                await level.add_xp(ctx.author.id, ctx.guild.id, xp_amount, member=ctx.author, check_mute=True, channel=ctx.channel)
        await self.update_stats(ctx.author.id, ctx.guild.id, won, bet, final_money if won else 0)

        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "game_play", 1)

    async def update_stats(self, user_id, guild_id, won, bet, win_amt):
        try:
            existing = await self.bot.db_manager.fetch_one(
                "game_stats", {"user_id": str(user_id), "guild_id": str(guild_id)}
            )
            if existing:
                data = {"total_bet": (existing.get("total_bet", 0) or 0) + bet}
                if won:
                    data["wins"] = (existing.get("wins", 0) or 0) + 1
                    data["total_won"] = (existing.get("total_won", 0) or 0) + win_amt
                else:
                    data["losses"] = (existing.get("losses", 0) or 0) + 1
                await self.bot.db_manager.update(
                    "game_stats",
                    {"user_id": str(user_id), "guild_id": str(guild_id)},
                    data,
                )
            else:
                data = {
                    "user_id": str(user_id),
                    "guild_id": str(guild_id),
                    "wins": 1 if won else 0,
                    "losses": 0 if won else 1,
                    "total_won": win_amt if won else 0,
                    "total_bet": bet,
                }
                await self.bot.db_manager.insert("game_stats", data)
        except Exception:
            pass

    # ══════════════ ТОГЛООМЫН КОМАНДУУД ══════════════
    async def start_game(self, ctx, command_name: str, amount: int, view_class, embed_title, embed_desc):
        """Ерөнхий тоглоом эхлүүлэгч"""
        if not await self.check_common_restrictions(ctx, amount):
            return
        # Күүки шалгах
        remaining = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, command_name)
        if remaining > 0:
            m, s = divmod(remaining, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ КҮҮКИ", description=f"**{m}м {s}с** хүлээх хэрэгтэй.", color=WARNING_COLOR))
        # Мөнгө хасах
        economy = self.bot.get_cog("Economy")
        await economy.update_balance(ctx.author.id, ctx.guild.id, -amount)
        self.set_cooldown(ctx.author.id, ctx.guild.id, command_name)
        view = view_class(self, ctx, amount)
        embed = discord.Embed(title=embed_title, description=embed_desc, color=GOLD_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(amount)}")
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='gamble', aliases=['gm'])
    async def gamble(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "gamble", amount, GambleView, "🎲 GAMBLE", f"Бооцоо: **{_format_money(amount)}**\n30% хожих магадлалтай.")

    @commands.command(name='coinflipgame', aliases=['cfgame', 'flipgame'])
    async def coinflip(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "coinflip", amount, CoinflipView, "🪙 COINFLIP", f"Бооцоо: **{_format_money(amount)}**\nHeads эсвэл Tails сонго!")

    @commands.command(name='slot', aliases=['sl'])
    async def slot(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "slot", amount, SlotsView, "🎰 SLOTS", f"Бооцоо: **{_format_money(amount)}**\nSPIN товчлуурыг дарж эргэлдүүл!")

    @commands.command(name='roulettegame', aliases=['rg'])
    async def roulette(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "roulette", amount, RouletteView, "🎡 ROULETTE", f"Бооцоо: **{_format_money(amount)}**\nУлаан, Хар, Ногоон сонго!")

    @commands.command(name='dice')
    async def dice(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "dice", amount, DiceView, "🎲 DICE", f"Бооцоо: **{_format_money(amount)}**\n1-6 тоо тааж 6x хожих!")

    @commands.command(name='rps', aliases=['rockpaperscissors'])
    async def rps(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        await self.start_game(ctx, "rps", amount, RPSView, "🪨📄✂️ RPS", f"Бооцоо: **{_format_money(amount)}**\nЧулуу, Даавуу, Хайч!")

    @commands.command(name='numberguess', aliases=['numguess'])
    async def numberguess(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        secret = random.randint(1, 10)
        view = NumberGuessView(self, ctx, amount, secret)
        embed = discord.Embed(title="🔢 NUMBER GUESS", description=f"Бооцоо: **{_format_money(amount)}**\n1-10 хооронд тоо таа! (3x)", color=GOLD_COLOR)
        embed.set_footer(text="15 секундын дотор сонго")
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='highlow', aliases=['hl'])
    async def highlow(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        view = HighLowView(self, ctx, amount)
        embed = discord.Embed(title="🎲 HIGH-LOW", description=f"Эхний тоо: **{view.first_number}**\nДараагийн тоо өндөр эсвэл доогуур?", color=GOLD_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(amount)} | 30 секундын дотор сонго")
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='blackjack', aliases=['bj'])
    async def blackjack(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        view = BlackjackView(ctx, self, amount)
        view.update_embed()
        view.message = await ctx.send(embed=view.embed, view=view)

    @commands.command(name='highcard', aliases=['war'])
    async def highcard(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        view = HighCardView(ctx, self, amount)
        embed = discord.Embed(title="🃏 HIGH CARD", description="Доорх товчийг дарж хөзрөө илрүүл!", color=GOLD_COLOR)
        embed.add_field(name="🎴 ТАНЫ КАРТ", value="???")
        embed.add_field(name="🃟 ДИЛЕР", value="???")
        embed.set_footer(text=f"Бооцоо: {_format_money(amount)}")
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name='crash')
    async def crash(self, ctx, amount_str: str):
        amount = await self._parse_amount(ctx, amount_str)
        if amount is False: return
        view = CrashView(self, ctx, amount)
        await view.start()

    @commands.command(name='trivia')
    @commands.cooldown(1, 15, commands.BucketType.user)
    async def trivia(self, ctx):
        if ctx.guild is None: return await ctx.send("❌ Серверт ашиглана уу.")
        question = random.choice(TRIVIA_QUESTIONS)
        answers = '\n'.join([f"{i+1}. {ans}" for i, ans in enumerate(question['answers'])])
        embed = discord.Embed(title="🧠 TRIVIA", description=f"**{question['question']}**\n\n{answers}", color=INFO_COLOR)
        embed.set_footer(text="Хариултын дугаарыг (1 эсвэл 2) бичнэ үү. 10 секунд байна.")
        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content in ['1', '2']

        try:
            msg = await self.bot.wait_for('message', timeout=10.0, check=check)
            answer_idx = int(msg.content) - 1
        except:
            return await ctx.send("⏰ Хугацаа дууссан!")

        xp = random.randint(5, 15)
        if answer_idx == question['correct']:
            await ctx.send(f"✅ Зөв! {ctx.author.mention} +{xp} XP")
            level = self.bot.get_cog("Leveling")
            if level and hasattr(level, 'add_xp'):
                await level.add_xp(ctx.author.id, ctx.guild.id, xp, member=ctx.author, check_mute=True, channel=ctx.channel)
        else:
            await ctx.send(f"❌ Буруу. Зөв хариулт: **{question['answers'][question['correct']]}**")
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog: await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "game_play", 1)

    @commands.command(name='rob')
    async def rob(self, ctx, target: discord.Member):
        if not await self.check_common_restrictions(ctx): return
        if target.id == ctx.author.id or target.bot:
            return await ctx.send(embed=discord.Embed(title="❌ Буруу", description="Өөртөө эсвэл ботод халдаж болохгүй.", color=ERROR_COLOR))
        cd = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, "rob")
        if cd:
            m, s = divmod(cd, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ Хүлээ", description=f"**{m}м {s}с** дараа дахин оролдоно уу.", color=WARNING_COLOR))
        self.set_cooldown(ctx.author.id, ctx.guild.id, "rob")
        economy = self.bot.get_cog("Economy")
        if random.random() < 0.3:
            steal = random.randint(100, 5000)
            await economy.update_balance(target.id, ctx.guild.id, -steal)
            await economy.update_balance(ctx.author.id, ctx.guild.id, steal)
            await self.update_stats(ctx.author.id, ctx.guild.id, True, 0, steal)
            embed = discord.Embed(title="🦹 Дээрэм амжилттай", description=f"**{steal:,}₮** дээрэмдлээ!", color=SUCCESS_COLOR)
        else:
            fine = random.randint(500, 2000)
            await economy.update_balance(ctx.author.id, ctx.guild.id, -fine)
            await economy.set_prison(ctx.author.id, ctx.guild.id, hours=2)
            embed = discord.Embed(title="🚔 Баригдлаа", description=f"**{fine:,}₮** торгууль, 2 цаг шоронд.", color=ERROR_COLOR)
        await ctx.send(embed=embed)

    @commands.command(name='hack')
    async def hack(self, ctx, target: discord.Member):
        if not await self.check_common_restrictions(ctx): return
        if target.id == ctx.author.id or target.bot:
            return await ctx.send(embed=discord.Embed(title="❌ Буруу", description="Өөртөө эсвэл ботод халдаж болохгүй.", color=ERROR_COLOR))
        cd = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, "hack")
        if cd:
            h, m = divmod(cd // 3600, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ Хүлээ", description=f"**{h}ц {m}м** дараа дахин оролдоно уу.", color=WARNING_COLOR))
        self.set_cooldown(ctx.author.id, ctx.guild.id, "hack")
        economy = self.bot.get_cog("Economy")
        target_bank = await economy.get_bank(target.id, ctx.guild.id)
        target_bal = await economy.get_balance(target.id, ctx.guild.id)
        if target_bank + target_bal <= 0:
            return await ctx.send(embed=discord.Embed(title="💸 Хоосон", description=f"{target.mention} данс хоосон.", color=WARNING_COLOR))
        if random.random() < 0.3:
            if target_bank > 0:
                hack_amt = random.randint(1000, min(target_bank, 10000))
                await economy.update_bank(target.id, ctx.guild.id, -hack_amt)
            else:
                hack_amt = random.randint(100, min(target_bal, 5000))
                await economy.update_balance(target.id, ctx.guild.id, -hack_amt)
            await economy.update_balance(ctx.author.id, ctx.guild.id, hack_amt)
            await self.update_stats(ctx.author.id, ctx.guild.id, True, 0, hack_amt)
            embed = discord.Embed(title="💻 Хакер амжилттай", description=f"**{hack_amt:,}₮** хулгайлсан!", color=SUCCESS_COLOR)
        else:
            fine = random.randint(2000, 8000)
            await economy.update_balance(ctx.author.id, ctx.guild.id, -fine)
            await economy.set_prison(ctx.author.id, ctx.guild.id, hours=2)
            embed = discord.Embed(title="🚔 Баригдлаа", description=f"**{fine:,}₮** торгууль, 2 цаг шоронд.", color=ERROR_COLOR)
        await ctx.send(embed=embed)

    @commands.command(name='cgive', aliases=['cgift'])
    async def cgive(self, ctx, target: discord.Member, amount: int):
        if not await self.check_common_restrictions(ctx): return
        cd = await self.is_on_cooldown(ctx.author.id, ctx.guild.id, "cgive")
        if cd:
            h, m = divmod(cd // 3600, 60)
            return await ctx.send(embed=discord.Embed(title="⏳ Хүлээ", description=f"**{h}ц {m}м** дараа бэлэг өгөх боломжтой.", color=WARNING_COLOR))
        economy = self.bot.get_cog("Economy")
        if amount <= 0 or amount > await economy.get_balance(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="❌ Алдаа", description="Дүн буруу эсвэл мөнгө хүрэлцэхгүй.", color=ERROR_COLOR))
        self.set_cooldown(ctx.author.id, ctx.guild.id, "cgive")
        await economy.update_balance(ctx.author.id, ctx.guild.id, -amount)
        await economy.update_balance(target.id, ctx.guild.id, amount)
        embed = discord.Embed(title="🎁 Бэлэг илгээгдлээ", description=f"{ctx.author.mention} → {target.mention} **{amount:,}₮**", color=SUCCESS_COLOR)
        await ctx.send(embed=embed)

    @commands.command(name='gamestats')
    async def gamestats(self, ctx):
        row = await self.bot.db_manager.fetch_one(
            "game_stats", {"user_id": str(ctx.author.id), "guild_id": str(ctx.guild.id)}
        )
        if not row:
            return await ctx.send(embed=discord.Embed(title="📊 Статистик байхгүй", description=f"{ctx.author.mention} тоглоом тоглоогүй.", color=WARNING_COLOR))
        wins = row.get("wins", 0) or 0
        losses = row.get("losses", 0) or 0
        total_won = row.get("total_won", 0) or 0
        total_bet = row.get("total_bet", 0) or 0
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        net = total_won - total_bet
        embed = discord.Embed(title=f"🎮 {ctx.author.display_name} - Тоглоомын статистик", color=GOLD_COLOR)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.add_field(name="🏆 Ялалт", value=str(wins), inline=True)
        embed.add_field(name="💀 Хожигдол", value=str(losses), inline=True)
        embed.add_field(name="📊 Хожих %", value=f"{win_rate:.1f}%", inline=True)
        embed.add_field(name="💰 Хожсон", value=f"+{total_won:,}₮", inline=True)
        embed.add_field(name="🎲 Тавьсан", value=f"-{total_bet:,}₮", inline=True)
        embed.add_field(name="📈 Цэвэр ашиг", value=f"{net:+,}₮", inline=True)
        await ctx.send(embed=embed)

    # ══════════════ PUBLIC API (LEADERBOARD-Д ЗОРИУЛСАН) ══════════════
    async def get_top_games(self, guild_id: int, limit=10, offset=0):
        rows = await self.bot.db_manager.fetch_all(
            "game_stats",
            {"guild_id": str(guild_id)},
            order_by="total_won",
            desc=True,
            limit=limit,
            offset=offset,
        )
        return [(int(r["user_id"]), r.get("total_won", 0)) for r in rows]

    # ═══ ТУСЛАХ (бооцоог унших) ═══
    async def _parse_amount(self, ctx, amount_str: str):
        economy = self.bot.get_cog("Economy")
        if not economy:
            await ctx.send("❌ Эдийн засаг ачаалагдаагүй.")
            return False
        if amount_str.lower() == 'all':
            amount = await economy.get_balance(ctx.author.id, ctx.guild.id)
            if amount <= 0:
                await ctx.send(embed=discord.Embed(title="❌ Мөнгөгүй", description="Танд мөнгө байхгүй.", color=ERROR_COLOR))
                return False
        else:
            try:
                amount = int(amount_str)
            except ValueError:
                await ctx.send(embed=discord.Embed(title="❌ Буруу формат", description="Тоо эсвэл 'all' гэж оруулна уу.", color=ERROR_COLOR))
                return False
        return amount

async def setup(bot):
    await bot.add_cog(Games(bot))