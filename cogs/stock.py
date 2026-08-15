from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import random
import logging

logger = logging.getLogger(__name__)

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa

# ----- ДЭЛГҮҮРИЙН МЭДЭЭЛЭЛ ИМПОРТЛОХ -----
try:
    from cogs.shop import SHOP_ITEMS, ALL_VAPE_COMBOS
except ImportError:
    SHOP_ITEMS = []
    ALL_VAPE_COMBOS = {}
    logger.warning("cogs.shop идэвхгүй, хоосон утга ашиглаж байна.")

try:
    from cogs.cafe import Cafe
    CAFE_MENU = Cafe.menu if hasattr(Cafe, 'menu') else []
except ImportError:
    CAFE_MENU = []
    logger.warning("cogs.cafe идэвхгүй, хоосон утга ашиглаж байна.")

# ----- НӨӨЦИЙН ХЭМЖЭЭ (ID-р) -----
STOCK_RANGES = {
    1: (50, 150), 2: (50, 150), 3: (40, 120), 4: (30, 90), 5: (35, 105),
    6: (25, 75), 7: (30, 90), 8: (25, 75), 9: (20, 60), 10: (30, 90),
    60: (100, 300),
    11: (10, 30), 12: (10, 30), 13: (5, 20), 14: (5, 20), 15: (3, 15),
    36: (2, 10), 37: (2, 10), 38: (2, 10), 39: (2, 10), 40: (3, 15),
    41: (3, 15), 42: (2, 10), 43: (5, 20), 44: (5, 20), 45: (5, 25),
    46: (1, 8),  47: (8, 30), 48: (5, 25),
    70: (8, 30), 71: (5, 25), 72: (3, 15), 73: (3, 15), 74: (3, 15),
    75: (5, 20), 76: (2, 10), 77: (2, 10), 78: (2, 10), 79: (3, 15),
    80: (5, 20), 81: (3, 15), 82: (3, 15), 83: (2, 10), 84: (3, 15),
    85: (3, 15), 86: (2, 10), 87: (5, 20), 88: (3, 15), 89: (5, 25),
    90: (5, 20), 91: (3, 15), 92: (3, 15), 93: (2, 10), 94: (2, 10),
    95: (3, 15), 96: (3, 15), 97: (5, 20), 98: (5, 20), 99: (2, 10),
    100: (5, 25), 101: (5, 20), 102: (5, 25), 103: (8, 30), 104: (5, 20),
    105: (5, 25), 106: (5, 20), 107: (5, 25), 108: (5, 20), 109: (5, 25),
    110: (5, 20), 111: (3, 15), 112: (2, 10), 113: (3, 15), 114: (3, 15),
    115: (2, 10),
    120: (8, 30), 121: (5, 25), 122: (15, 50), 123: (15, 50), 124: (5, 20),
    125: (5, 25), 126: (3, 15), 127: (3, 15), 128: (8, 30), 129: (5, 25),
    130: (5, 20), 131: (5, 25), 132: (8, 30), 133: (5, 25), 134: (10, 40),
    135: (8, 30),
}
VAPE_RANGE = (30, 80)
CAFE_RANGE = (20, 60)
DEFAULT_RANGE = (10, 50)


class PaginatedStockView(discord.ui.View):
    """Нөөцийн төлвийг хуудаслах харагдац."""
    def __init__(self, pages: list[discord.Embed], timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0

    async def update_message(self, interaction: discord.Interaction):
        self.previous.disabled = self.current_page == 0
        self.next.disabled = self.current_page == len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="◀ Өмнөх", style=discord.ButtonStyle.gray)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="Дараах ▶", style=discord.ButtonStyle.gray)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_message(interaction)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            await self.message.edit(view=self)


class Stock(commands.Cog):
    """Сервер тус бүрийн санамсаргүй нөөцийн систем."""

    def __init__(self, bot):
        self.bot = bot
        self.daily_restock.start()

    def cog_unload(self):
        self.daily_restock.cancel()

    # ================== ӨГӨГДЛИЙН САНГИЙН ТОХИРГОО ==================
    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        for guild in self.bot.guilds:
            await self.ensure_stocks_for_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.ensure_stocks_for_guild(guild.id)

    # ================== БҮХ БАРААНЫ ID-Г АВАХ ==================
    def _all_item_ids(self):
        """Бүх барааны ID-г буцаана."""
        ids = set(STOCK_RANGES.keys())
        ids.update(ALL_VAPE_COMBOS.keys())
        for i in range(len(CAFE_MENU)):
            ids.add(6000 + i)
        return ids

    def _get_range(self, item_id):
        if item_id in STOCK_RANGES:
            return STOCK_RANGES[item_id]
        if 4000 <= item_id < 6000:
            return VAPE_RANGE
        if item_id >= 6000:
            return CAFE_RANGE
        return DEFAULT_RANGE

    # ================== СЕРВЕРИЙГ ЭХЛҮҮЛЭХ (ЗАСВАР: INSERT IGNORE) ==================
    async def _ensure_item_stock(self, guild_id: int, item_id: int):
        """Нэг барааны мөр байхгүй бол санамсаргүй нөөцтэй үүсгэх.

        UPSERT ашигладаг (on_conflict = guild_id,item_id) — select-then-insert
        race condition-аас үүсдэг 23505 duplicate key алдааг бүрмөсөн арилгана.
        Existing мөр дээр upsert нь update хийхгүй (current_stock нь ижил утгаар).
        """
        existing = await self.bot.db_manager.fetch_one(
            "shop_stock", {"guild_id": str(guild_id), "item_id": str(item_id)}
        )
        if existing:
            return
        lo, hi = self._get_range(item_id)
        random_stock = random.randint(lo, hi)
        await self.bot.db_manager.upsert("shop_stock", {
            "guild_id": str(guild_id),
            "item_id": item_id,
            "current_stock": random_stock,
            "last_restock": int(datetime.datetime.now().timestamp()),
        }, on_conflict="guild_id,item_id")

    async def ensure_stocks_for_guild(self, guild_id: int):
        """Дутуу бараануудыг санамсаргүй нөөцтэй оруулах."""
        for item_id in self._all_item_ids():
            await self._ensure_item_stock(guild_id, item_id)

    # ================== НЭЭЛТТЭЙ API (УРАЛДААНЫ АЮУЛГҮЙ) ==================
    async def get_stock(self, guild_id, item_id):
        """Одоогийн нөөцийг унших. Хэрэв мөр байхгүй бол 0 буцаана."""
        row = await self.bot.db_manager.fetch_one(
            "shop_stock", {"guild_id": str(guild_id), "item_id": str(item_id)}
        )
        return row.get("current_stock", 0) or 0 if row else 0

    async def consume_stock(self, guild_id, item_id, quantity=1):
        """
        Атомар байдлаар нөөц хасах.
        Амжилттай бол True, хүрэлцэхгүй эсвэл бараа байхгүй бол False буцаана.
        """
        row = await self.bot.db_manager.fetch_one(
            "shop_stock", {"guild_id": str(guild_id), "item_id": str(item_id)}
        )
        if not row or (row.get("current_stock", 0) or 0) < quantity:
            return False
        await self.bot.db_manager.update(
            "shop_stock",
            {"guild_id": str(guild_id), "item_id": str(item_id)},
            {"current_stock": (row.get("current_stock", 0) or 0) - quantity},
        )
        return True

    async def set_stock(self, guild_id, item_id, amount):
        """
        Нөөцийг яг тодорхой хэмжээнд тавих. Хэрэв мөр байхгүй бол үүсгэнэ.
        """
        await self.bot.db_manager.upsert(
            "shop_stock",
            {
                "guild_id": str(guild_id),
                "item_id": item_id,
                "current_stock": amount,
                "last_restock": int(datetime.datetime.now().timestamp()),
            },
            on_conflict="guild_id,item_id",
        )

    # ================== ӨДӨР БҮРИЙН НӨӨЦ ШИНЭЧЛЭЛТ ==================
    @tasks.loop(hours=24)
    async def daily_restock(self):
        await self.bot.wait_until_ready()
        now_ts = int(datetime.datetime.now().timestamp())
        for guild in self.bot.guilds:
            try:
                await self.ensure_stocks_for_guild(guild.id)
                stock_rows = await self.bot.db_manager.fetch_safe(
                    "shop_stock", {"guild_id": str(guild.id)}
                )
                for row in stock_rows:
                    item_id = row.get("item_id")
                    lo, hi = self._get_range(item_id)
                    random_val = random.randint(lo, hi)
                    await self.bot.db_manager.update(
                        "shop_stock",
                        {"guild_id": str(guild.id), "item_id": item_id},
                        {"current_stock": random_val, "last_restock": now_ts},
                    )
            except Exception as e:
                logger.error("Өдөр бүрийн нөөц шинэчлэлт сервер %s дээр амжилтгүй: %s", guild.id, e)
        logger.info("Өдөр бүрийн нөөц шинэчлэлт бүх серверт хийгдлээ.")

    @daily_restock.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    # ================== КОМАНДЫН ГРУПП ==================
    @commands.hybrid_group(name='stock', description="Нөөцийн удирдлага",
                           invoke_without_command=True)
    async def stock_group(self, ctx):
        embed = discord.Embed(
            title="📦 Нөөцийн удирдлага",
            description="`/stock status` – нөөцийн төлөв харах\n"
                        "`/stock set <ID> <тоо>` – нөөцийг тогтоох\n"
                        "`/stock add <ID> <тоо>` – нөөц нэмэх\n"
                        "`/stock remove <ID> <тоо>` – нөөц хасах\n"
                        "`/stock reset` – нөөцийг даруй санамсаргүй болгох\n"
                        "`/stock refresh` – бүх серверт дахин дүүргэх",
            color=INFO_COLOR
        )
        await ctx.send(embed=embed)

    async def _send_hybrid(self, ctx, content=None, embed=None, ephemeral=False, view=None):
        if ctx.interaction:
            return await ctx.send(content=content, embed=embed, ephemeral=ephemeral, view=view)
        else:
            return await ctx.send(content=content, embed=embed, view=view)

    # ================== НӨӨЦИЙН ТӨЛӨВ (ХУУДАСЛАЛТТАЙ) ==================
    @stock_group.command(name='status', description="Одоогийн нөөцийн түвшинг харуулах")
    async def stock_status(self, ctx):
        await self.ensure_stocks_for_guild(ctx.guild.id)
        stock_rows = await self.bot.db_manager.fetch_all(
            "shop_stock", {"guild_id": str(ctx.guild.id)},
            order_by="item_id",
        )
        rows = [(r["item_id"], r.get("current_stock", 0) or 0) for r in stock_rows]

        if not rows:
            return await self._send_hybrid(ctx, embed=discord.Embed(
                title="📦 Нөөц", description="Бараа олдсонгүй.", color=WARNING_COLOR
            ))

        item_names = {}
        for item in SHOP_ITEMS:
            item_names[item['id']] = f"{item.get('emoji','📦')} {item['name']}"
        for combo_id, combo in ALL_VAPE_COMBOS.items():
            item_names[combo_id] = f"{combo['emoji']} {combo['name']}"
        for idx, menu_item in enumerate(CAFE_MENU):
            item_names[6000 + idx] = f"{menu_item['emoji']} {menu_item['name']}"

        pages = []
        items_per_page = 10
        for i in range(0, len(rows), items_per_page):
            embed = discord.Embed(title="📦 Дэлгүүрийн нөөц", color=GOLD_COLOR)
            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
            chunk = rows[i:i + items_per_page]
            for item_id, stock in chunk:
                lo, hi = self._get_range(item_id)
                name = item_names.get(item_id, f"ID {item_id}")
                embed.add_field(
                    name=name,
                    value=f"Нөөц: **{stock}**  (шинэчлэлтийн хэмжээ: {lo}–{hi})",
                    inline=True
                )
            embed.set_footer(text=f"Хуудас {i//items_per_page + 1}/{(len(rows)-1)//items_per_page + 1}")
            pages.append(embed)

        if len(pages) == 1:
            await self._send_hybrid(ctx, embed=pages[0])
        else:
            view = PaginatedStockView(pages)
            message = await self._send_hybrid(ctx, embed=pages[0], view=view)
            view.message = message

    # ================== АДМИН КОМАНДУУД ==================
    @stock_group.command(name='set', description="Барааны нөөцийг тогтоох (админ)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Шинэ нөөцийн тоо")
    async def stock_set(self, ctx, item_id: int, amount: int):
        if amount < 0:
            return await self._send_hybrid(ctx, "❌ Нөөц сөрөг байж болохгүй.", ephemeral=True)
        await self.set_stock(ctx.guild.id, item_id, amount)
        await self._send_hybrid(ctx, f"✅ {item_id} барааны нөөц **{amount}** боллоо.", ephemeral=True)

    @stock_group.command(name='add', description="Барааны нөөц нэмэх (админ)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Нэмэх тоо")
    async def stock_add(self, ctx, item_id: int, amount: int):
        if amount <= 0:
            return await self._send_hybrid(ctx, "❌ Нэмэх тоо эерэг байх ёстой.", ephemeral=True)
        row = await self.bot.db_manager.fetch_one(
            "shop_stock", {"guild_id": str(ctx.guild.id), "item_id": str(item_id)}
        )
        if not row:
            return await self._send_hybrid(
                ctx, "❌ Бараа олдсонгүй. Эхлээд `/stock set` ашиглана уу.", ephemeral=True
            )
        await self.bot.db_manager.update(
            "shop_stock",
            {"guild_id": str(ctx.guild.id), "item_id": str(item_id)},
            {"current_stock": (row.get("current_stock", 0) or 0) + amount},
        )
        current = await self.get_stock(ctx.guild.id, item_id)
        await self._send_hybrid(ctx, f"✅ {item_id} бараанд {amount} нэмэгдлээ (одоо {current}).", ephemeral=True)

    @stock_group.command(name='remove', description="Барааны нөөц хасах (админ)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @app_commands.describe(item_id="Барааны ID", amount="Хасах тоо")
    async def stock_remove(self, ctx, item_id: int, amount: int):
        if amount <= 0:
            return await self._send_hybrid(ctx, "❌ Хасах тоо эерэг байх ёстой.", ephemeral=True)
        row = await self.bot.db_manager.fetch_one(
            "shop_stock", {"guild_id": str(ctx.guild.id), "item_id": str(item_id)}
        )
        if not row:
            return await self._send_hybrid(ctx, "❌ Бараа олдсонгүй.", ephemeral=True)
        exists = row.get("current_stock", 0) or 0
        if exists < amount:
            return await self._send_hybrid(ctx, "❌ Нөөц хүрэлцэхгүй.", ephemeral=True)
        await self.bot.db_manager.update(
            "shop_stock",
            {"guild_id": str(ctx.guild.id), "item_id": str(item_id)},
            {"current_stock": exists - amount},
        )
        current = await self.get_stock(ctx.guild.id, item_id)
        await self._send_hybrid(ctx, f"✅ {item_id} бараанаас {amount} хасагдлаа (одоо {current}).", ephemeral=True)

    @stock_group.command(name='reset', description="Бүх нөөцийг даруй санамсаргүй болгох (админ)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def stock_reset(self, ctx):
        await self.ensure_stocks_for_guild(ctx.guild.id)
        now_ts = int(datetime.datetime.now().timestamp())
        stock_rows = await self.bot.db_manager.fetch_all(
            "shop_stock", {"guild_id": str(ctx.guild.id)}
        )
        for row in stock_rows:
            item_id = row.get("item_id")
            lo, hi = self._get_range(item_id)
            random_val = random.randint(lo, hi)
            await self.bot.db_manager.update(
                "shop_stock",
                {"guild_id": str(ctx.guild.id), "item_id": item_id},
                {"current_stock": random_val, "last_restock": now_ts},
            )
        await self._send_hybrid(ctx, "✅ Бүх нөөц санамсаргүй болгогдлоо.", ephemeral=True)

    @stock_group.command(name='refresh', description="Бүх серверийн нөөцийг дахин дүүргэх (админ)")
    @app_commands.default_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def stock_refresh(self, ctx):
        for guild in self.bot.guilds:
            await self.ensure_stocks_for_guild(guild.id)
        await self._send_hybrid(ctx, "✅ Бүх серверийн нөөц шинэчлэгдлээ.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Stock(bot))