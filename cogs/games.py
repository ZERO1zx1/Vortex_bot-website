from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord.ui import View, Button
from discord import ButtonStyle
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

TRIVIA_QUESTIONS = [
    {"question": "Монгол Улсын нийслэл хот аль нь вэ?", "answers": ["Улаанбаатар", "Эрдэнэт"], "correct": 0},
    {"question": "Нэг жил хэдэн сартай вэ?", "answers": ["12 сар", "10 сар"], "correct": 0},
    {"question": "Хүн хэдэн хөлтэй вэ?", "answers": ["2", "4"], "correct": 0},
    {"question": "Нарны аймагт хэдэн гариг байдаг вэ?", "answers": ["8", "9"], "correct": 0},
    {"question": "Ус хэдэн градуст буцалдаг вэ?", "answers": ["100°C", "90°C"], "correct": 0},
    {"question": "Чингис хаан Монголыг хэдэн онд нэгтгэсэн бэ?", "answers": ["1206 он", "1306 он"], "correct": 0},
    {"question": "Хүн жилд хэдэн удаа амьсгалдаг вэ?", "answers": ["Ойролцоогоор 8 сая", "Ойролцоогоор 800 мянга"], "correct": 0},
    {"question": "Хамгийн том хөхтөн амьтан аль нь вэ?", "answers": ["Хөх халим", "Африкийн заан"], "correct": 0},
]


# ══════════════ ТОГЛООМЫН VIEW-үүд ══════════════

class GambleView(View):
    """🎲 GAMBLE — 30% хожих магадлалтай, 5x"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="БООЦОО ТАВИХ 🎲", style=ButtonStyle.danger)
    async def roll(self, interaction, button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        if random.random() < 0.30:
            winnings = self.amount * 5
            await self.cog.give_rewards(self.ctx, winnings, 10, won=True, bet=self.amount)
            embed = discord.Embed(title="🎉 ЯЛАЛТ!", description=f"Таны {self.ctx.author.mention} дугарилтаар хожлоо!\n+{_format_money(winnings)} (5x)", color=SUCCESS_COLOR)
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed = discord.Embed(title="💀 ХОЖИГДЛОО!", description=f"Таны {self.ctx.author.mention} хожигдлоо.\n-{_format_money(self.amount)}", color=ERROR_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()


class CoinflipView(View):
    """🪙 COINFLIP — 2x"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.choice = None
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def decide(self, interaction, choice):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        result = random.choice(["heads", "tails"])
        label = "🌕 HEADS" if result == "heads" else "🌑 TAILS"
        if choice == result:
            winnings = self.amount * 2
            await self.cog.give_rewards(self.ctx, winnings, 8, won=True, bet=self.amount)
            embed = discord.Embed(title="🎉 ЯЛАЛТ!", description=f"Зоос: **{label}**\nТаны {self.ctx.author.mention} сонголт таарлаа! +{_format_money(winnings)} (2x)", color=SUCCESS_COLOR)
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed = discord.Embed(title="💀 ХОЖИГДЛОО!", description=f"Зоос: **{label}**\nТаны {self.ctx.author.mention} сонголт таарахгүй. -{_format_money(self.amount)}", color=ERROR_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="🌕 HEADS", style=ButtonStyle.primary)
    async def heads(self, interaction, button):
        await interaction.response.defer()
        await self.decide(interaction, "heads")

    @discord.ui.button(label="🌑 TAILS", style=ButtonStyle.secondary)
    async def tails(self, interaction, button):
        await interaction.response.defer()
        await self.decide(interaction, "tails")


class SlotsView(View):
    """🎰 SLOTS — 3 ижил тэмдэг 50x, 2 ижил 3x"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="SPIN 🎰", style=ButtonStyle.danger)
    async def spin(self, interaction, button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        symbols = ["🍒", "🍋", "🍇", "💎", "7️⃣", "🔔", "⭐"]
        r = [random.choice(symbols) for _ in range(3)]
        display = "   ".join(r)
        embed = discord.Embed(title="🎰 SLOTS", description=f"**{display}**", color=INFO_COLOR)
        if r[0] == r[1] == r[2]:
            winnings = self.amount * 50
            await self.cog.give_rewards(self.ctx, winnings, 25, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЖЕКПОТ!", value=f"+{_format_money(winnings)} (50x)", inline=False)
            embed.color = SUCCESS_COLOR
        elif r[0] == r[1] or r[1] == r[2] or r[0] == r[2]:
            winnings = self.amount * 3
            await self.cog.give_rewards(self.ctx, winnings, 8, won=True, bet=self.amount)
            embed.add_field(name="✅ Хоёр ижил!", value=f"+{_format_money(winnings)} (3x)", inline=False)
            embed.color = SUCCESS_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 Олдсонгүй", value=f"-{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()


class RouletteView(View):
    """🎡 ROULETTE — Улаан/Хар 2x, Ногоон 14x"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def spin(self, interaction, choice):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        n = random.randint(0, 36)
        color = "green" if n == 0 else ("red" if n % 2 == 1 else "black")
        color_label = {"red": "🔴 УЛААН", "black": "⚫ ХАР", "green": "🟢 НОГООН"}[color]
        multiplier = {"red": 2, "black": 2, "green": 14}[choice]
        embed = discord.Embed(title="🎡 ROULETTE", description=f"Тоо: **{n}** — {color_label}", color=INFO_COLOR)
        if choice == color:
            winnings = self.amount * multiplier
            await self.cog.give_rewards(self.ctx, winnings, 10, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЯЛАЛТ!", value=f"+{_format_money(winnings)} ({multiplier}x)", inline=False)
            embed.color = SUCCESS_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 ХОЖИГДЛОО!", value=f"-{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="🔴 УЛААН", style=ButtonStyle.danger)
    async def red(self, interaction, button):
        await interaction.response.defer()
        await self.spin(interaction, "red")

    @discord.ui.button(label="⚫ ХАР", style=ButtonStyle.secondary)
    async def black(self, interaction, button):
        await interaction.response.defer()
        await self.spin(interaction, "black")

    @discord.ui.button(label="🟢 НОГООН", style=ButtonStyle.success)
    async def green(self, interaction, button):
        await interaction.response.defer()
        await self.spin(interaction, "green")


class DiceView(View):
    """🎲 DICE — 1-6 тоо тааж 6x"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def roll(self, interaction, guess):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        result = random.randint(1, 6)
        dice_emoji = ["", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"][result]
        embed = discord.Embed(title="🎲 DICE", description=f"Шоо буулаа: **{dice_emoji}** (тоо {result})", color=INFO_COLOR)
        if guess == result:
            winnings = self.amount * 6
            await self.cog.give_rewards(self.ctx, winnings, 12, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЯЛАЛТ!", value=f"+{_format_money(winnings)} (6x)", inline=False)
            embed.color = SUCCESS_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 ХОЖИГДЛОО!", value=f"Та {guess} гэж таасан. -{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="1️⃣", style=ButtonStyle.secondary)
    async def d1(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 1)

    @discord.ui.button(label="2️⃣", style=ButtonStyle.secondary)
    async def d2(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 2)

    @discord.ui.button(label="3️⃣", style=ButtonStyle.secondary)
    async def d3(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 3)

    @discord.ui.button(label="4️⃣", style=ButtonStyle.secondary)
    async def d4(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 4)

    @discord.ui.button(label="5️⃣", style=ButtonStyle.secondary)
    async def d5(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 5)

    @discord.ui.button(label="6️⃣", style=ButtonStyle.secondary)
    async def d6(self, interaction, button):
        await interaction.response.defer()
        await self.roll(interaction, 6)


class RPSView(View):
    """🪨📄✂️ RPS — хожиход 2x"""
    CHOICES = {"rock": "🪨 Чулуу", "paper": "📄 Даавуу", "scissors": "✂️ Хайч"}
    BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}

    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=30)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def play(self, interaction, choice):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        bot_choice = random.choice(list(self.CHOICES.keys()))
        embed = discord.Embed(title="🪨📄✂️ RPS", description=f"Та: **{self.CHOICES[choice]}**\nБот: **{self.CHOICES[bot_choice]}**", color=INFO_COLOR)
        if choice == bot_choice:
            await self.cog.give_rewards(self.ctx, 0, 4, won=False, bet=self.amount)
            embed.add_field(name="🤝 ХАМТРАЛ!", value=f"Бооцоо буцаж ирлээ: {_format_money(self.amount)}", inline=False)
            embed.color = WARNING_COLOR
        elif self.BEATS[choice] == bot_choice:
            winnings = self.amount * 2
            await self.cog.give_rewards(self.ctx, winnings, 8, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЯЛАЛТ!", value=f"+{_format_money(winnings)} (2x)", inline=False)
            embed.color = SUCCESS_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 ХОЖИГДЛОО!", value=f"-{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="🪨 Чулуу", style=ButtonStyle.primary)
    async def rock(self, interaction, button):
        await interaction.response.defer()
        await self.play(interaction, "rock")

    @discord.ui.button(label="📄 Даавуу", style=ButtonStyle.primary)
    async def paper(self, interaction, button):
        await interaction.response.defer()
        await self.play(interaction, "paper")

    @discord.ui.button(label="✂️ Хайч", style=ButtonStyle.primary)
    async def scissors(self, interaction, button):
        await interaction.response.defer()
        await self.play(interaction, "scissors")


class NumberGuessView(View):
    """🔢 NUMBER GUESS — 1-10, 3x"""
    def __init__(self, cog, ctx, amount, secret):
        super().__init__(timeout=15)
        self.cog, self.ctx, self.amount, self.secret = cog, ctx, amount, secret
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def guess(self, interaction, number):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        embed = discord.Embed(title="🔢 NUMBER GUESS", description=f"Нууц тоо: **{self.secret}**\nТаны таахсан тоо: **{number}**", color=INFO_COLOR)
        if number == self.secret:
            winnings = self.amount * 3
            await self.cog.give_rewards(self.ctx, winnings, 12, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЯЛАЛТ!", value=f"+{_format_money(winnings)} (3x)", inline=False)
            embed.color = SUCCESS_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 ХОЖИГДЛОО!", value=f"-{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="1-3", style=ButtonStyle.secondary)
    async def low(self, interaction, button):
        await interaction.response.defer()
        await self.guess(interaction, random.randint(1, 3))

    @discord.ui.button(label="4-7", style=ButtonStyle.secondary)
    async def mid(self, interaction, button):
        await interaction.response.defer()
        await self.guess(interaction, random.randint(4, 7))

    @discord.ui.button(label="8-10", style=ButtonStyle.secondary)
    async def high(self, interaction, button):
        await interaction.response.defer()
        await self.guess(interaction, random.randint(8, 10))

    async def on_timeout(self):
        try:
            embed = discord.Embed(title="⏰ ХУГАЦАА ДУУССАН", description=f"Нууц тоо **{self.secret}** байсан.", color=ERROR_COLOR)
            await self.cog.give_rewards(self.ctx, -self.amount, 2, won=False, bet=self.amount)
            await self.message.edit(embed=embed, view=self)
        except Exception:
            pass


class HighCardView(View):
    """🃏 HIGH CARD — таны карт > дилер 2x"""
    def __init__(self, ctx, cog, amount):
        super().__init__(timeout=30)
        self.ctx, self.cog, self.amount = ctx, cog, amount
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🃏 ХӨЗРӨӨ ИЛРҮҮЛЭХ", style=ButtonStyle.danger)
    async def reveal(self, interaction, button):
        for child in self.children:
            child.disabled = True
        await self.message.edit(view=self)
        player = random.randint(1, 13)
        dealer = random.randint(1, 13)
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        p_label = names.get(player, str(player))
        d_label = names.get(dealer, str(dealer))
        embed = discord.Embed(title="🃏 HIGH CARD", description=f"🎴 ТАНЫ КАРТ: **{p_label}**\n🃟 ДИЛЕР: **{d_label}**", color=INFO_COLOR)
        if player > dealer:
            winnings = self.amount * 2
            await self.cog.give_rewards(self.ctx, winnings, 10, won=True, bet=self.amount)
            embed.add_field(name="🎉 ЯЛАЛТ!", value=f"+{_format_money(winnings)} (2x)", inline=False)
            embed.color = SUCCESS_COLOR
        elif player == dealer:
            await self.cog.give_rewards(self.ctx, 0, 4, won=False, bet=self.amount)
            embed.add_field(name="🤝 ТЭНЦЭЭ!", value=f"Бооцоо буцаж ирлээ: {_format_money(self.amount)}", inline=False)
            embed.color = WARNING_COLOR
        else:
            await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
            embed.add_field(name="💀 ХОЖИГДЛОО!", value=f"-{_format_money(self.amount)}", inline=False)
            embed.color = ERROR_COLOR
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)}")
        await self.message.edit(embed=embed, view=self)
        self.stop()


class CrashView(View):
    """💥 CRASH — өсөж байхад CASH OUT дарж хож"""
    def __init__(self, cog, ctx, amount):
        super().__init__(timeout=20)
        self.cog, self.ctx, self.amount = cog, ctx, amount
        self.multiplier = 1.00
        self.crash_point = max(1.01, random.expovariate(0.5) + 1.0)
        self.running = True
        self.message = None

    async def interaction_check(self, interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ таны тоглоом биш!", ephemeral=True)
            return False
        return True

    async def start(self):
        self.cashout.disabled = False
        embed = discord.Embed(title="💥 CRASH", description=f"Хүчин зүйл: **1.00x**\n📈 Өсөж байна...", color=INFO_COLOR)
        embed.set_footer(text=f"Бооцоо: {_format_money(self.amount)} — CASH OUT эсвэл CRASH хүлээ")
        self.message = await self.ctx.send(embed=embed, view=self)
        while self.running and self.multiplier < self.crash_point:
            await asyncio.sleep(1)
            self.multiplier = round(self.multiplier + random.uniform(0.05, 0.15), 2)
            try:
                embed = discord.Embed(title="💥 CRASH", description=f"Хүчин зүйл: **{self.multiplier:.2f}x**\n📈 Өсөж байна...", color=WARNING_COLOR)
                embed.set_footer(text=f"CASH OUT дарж хож! Бооцоо: {_format_money(self.amount)}")
                await self.message.edit(embed=embed, view=self)
            except Exception:
                break
        if self.running:
            self.running = False
            for child in self.children:
                child.disabled = True
            try:
                embed = discord.Embed(title="💥 CRASH!", description=f"Хүчин зүйл **{self.crash_point:.2f}x**-д уналаа!\n😢 Хожигдлоо: **-{_format_money(self.amount)}**", color=ERROR_COLOR)
                await self.cog.give_rewards(self.ctx, -self.amount, 3, won=False, bet=self.amount)
                await self.message.edit(embed=embed, view=self)
            except Exception:
                pass
            self.stop()

    @discord.ui.button(label="💰 CASH OUT", style=ButtonStyle.success)
    async def cashout(self, interaction, button):
        if not self.running:
            await interaction.response.send_message("⏰ Тоглоом дууссан!", ephemeral=True)
            return
        self.running = False
        for child in self.children:
            child.disabled = True
        winnings = int(self.amount * self.multiplier)
        await self.cog.give_rewards(self.ctx, winnings, 10, won=True, bet=self.amount)
        embed = discord.Embed(title="💰 CASH OUT!", description=f"**{self.multiplier:.2f}x**-д гарлаа!\n🎉 +{_format_money(winnings)}", color=SUCCESS_COLOR)
        embed.set_footer(text=f"CRASH цэг: {self.crash_point:.2f}x")
        try:
            await self.message.edit(embed=embed, view=self)
        except Exception:
            pass
        self.stop()

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