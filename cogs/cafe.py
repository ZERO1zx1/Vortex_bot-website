from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Select, View
import time

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
GOLD_COLOR = 0xfab387
WARNING_COLOR = 0xf9e2af

class CafeView(View):
    def __init__(self, ctx, cafe_cog):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cafe = cafe_cog
        self.message = None

        options = []
        for i, item in enumerate(self.cafe.menu[:25]):
            options.append(
                discord.SelectOption(
                    label=f"{item['emoji']} {item['name']} - {item['price']:,}₮",
                    value=str(i),
                    description=item.get('desc', '')[:50]
                )
            )
        self.select = Select(placeholder="🍽️ Хоол сонгох", options=options)
        self.select.callback = self.select_callback
        self.add_item(self.select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ Энэ цэс таных биш!", ephemeral=True)
            return

        await interaction.response.defer()

        idx = int(self.select.values[0])
        item = self.cafe.menu[idx]

        economy = self.ctx.bot.get_cog("Economy")
        if not economy:
            await interaction.followup.send("❌ Эдийн засгийн систем ажиллахгүй байна.", ephemeral=True)
            return

        guild_id = self.ctx.guild.id
        if await economy.is_in_prison(self.ctx.author.id, guild_id):
            await interaction.followup.send("🚔 Шоронд хоол захиалах боломжгүй.", ephemeral=True)
            return

        bal = await economy.get_balance(self.ctx.author.id, guild_id)
        if bal < item['price']:
            embed = discord.Embed(
                title="❌ Мөнгө хүрэлцэхгүй",
                description=f"**{item['emoji']} {item['name']}** авахад **{item['price']:,}₮** хэрэгтэй.\nТаны үлдэгдэл: `{bal:,}₮`",
                color=ERROR_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        stock_cog = self.ctx.bot.get_cog("Stock")
        if stock_cog:
            food_id = 6000 + idx
            if not await stock_cog.consume_stock(guild_id, food_id, 1):
                embed = discord.Embed(
                    title="❌ ДУУССАН",
                    description="Уучлаарай, энэ хоол одоогоор дууссан.",
                    color=ERROR_COLOR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return

        await economy.update_balance(self.ctx.author.id, guild_id, -item['price'])

        shop_cog = self.ctx.bot.get_cog("ShopCog")
        if shop_cog:
            food_id = 6000 + idx
            await shop_cog.add_item(self.ctx.author.id, guild_id, food_id, 1)

        embed = discord.Embed(
            title="✅ Хоол захиалагдлаа!",
            description=f"**{item['emoji']} {item['name']}** худалдаж авлаа.\nИдэхдээ `{self.ctx.prefix}dine {idx+1}`",
            color=SUCCESS_COLOR
        )
        await interaction.message.edit(embed=embed, view=None)


class Cafe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.menu = [
            # Уух зүйлс
            {"name": "Айс Американо",   "emoji": "🧊☕", "price": 5500,  "category": "drink",  "desc": "Сэрүүн, хүчтэй", "buff": "xp_boost",   "xp_mult": 1.5, "duration": 30},
            {"name": "Халуун шоколад",  "emoji": "🍫☕", "price": 6500,  "category": "drink",  "desc": "Чихэрлэг",       "buff": "xp_boost",   "xp_mult": 1.5, "duration": 30},
            {"name": "Эрчим хүчний ундаа","emoji": "⚡",  "price": 8000,  "category": "drink",  "desc": "Эрч хүч",        "buff": "work_mult",  "money_mult": 2, "duration": 30},
            {"name": "Сүүтэй цай",       "emoji": "🧋",   "price": 3500,  "category": "drink",  "desc": "Уламжлалт",     "buff": "xp_boost",   "xp_mult": 1.3, "duration": 20},
            {"name": "Эспрессо",         "emoji": "☕",    "price": 4500,  "category": "drink",  "desc": "Жижиг, хүчтэй", "buff": "xp_boost",   "xp_mult": 1.3, "duration": 20},
            {"name": "Каппучино",        "emoji": "☕",    "price": 6000,  "category": "drink",  "desc": "Сүүтэй, зөөлөн", "buff": "xp_boost",   "xp_mult": 1.7, "duration": 35},
            {"name": "Мока латте",       "emoji": "🍫☕", "price": 7000,  "category": "drink",  "desc": "Шоколадтай кофе","buff": "xp_boost",   "xp_mult": 2,   "duration": 40},
            # Зууш / Амттан
            {"name": "Сармистай шарсан талх","emoji": "🧄🍞","price": 4000,"category": "snack", "desc": "Шаржигнасан",  "buff": "xp_boost",   "xp_mult": 1.5, "duration": 40},
            {"name": "Шарсан төмс",      "emoji": "🍟",   "price": 7000,  "category": "snack", "desc": "Давстай",      "buff": "xp_boost",   "xp_mult": 1.5, "duration": 40},
            {"name": "Чизкейк",          "emoji": "🍰",   "price": 9000,  "category": "snack", "desc": "Зөөлөн, амтат","buff": "xp_boost",   "xp_mult": 2,   "duration": 60},
            {"name": "Гүзээлзгэнэтэй бялуу","emoji": "🍰","price": 8500,"category": "snack", "desc": "Шинэ жимстэй","buff": "xp_boost",   "xp_mult": 2,   "duration": 60},
            {"name": "Макарон",          "emoji": "🍬",   "price": 5000,  "category": "snack", "desc": "Франц амттан", "buff": "xp_boost",   "xp_mult": 1.8, "duration": 45},
            {"name": "Донут",            "emoji": "🍩",   "price": 4500,  "category": "snack", "desc": "Шоколадтай",  "buff": "xp_boost",   "xp_mult": 1.5, "duration": 35},
            # Үндсэн хоол
            {"name": "Халуун хотдог",    "emoji": "🌭",   "price": 6500,  "category": "main",  "desc": "Гахайн махтай","buff": "xp_boost",   "xp_mult": 2,   "duration": 50},
            {"name": "Тахианы сэндвич",  "emoji": "🥪",   "price": 9500,  "category": "main",  "desc": "Шинэ ногоотой","buff": "xp_boost",   "xp_mult": 2,   "duration": 50},
            {"name": "Клаб Сэндвич",     "emoji": "🥪🍟","price": 12500, "category": "main",  "desc": "Давхар давхаргатай","buff": "xp_boost","xp_mult": 2.5,"duration": 60},
            {"name": "Шарсан тахианы далавч","emoji": "🍗","price": 18000,"category": "main","desc": "Халуун ногоотой","buff": "xp_boost","xp_mult": 3,"duration": 70},
            {"name": "Рамэн гоомон",     "emoji": "🍜",   "price": 16000, "category": "main", "desc": "Халуун шөлтэй","buff": "xp_boost","xp_mult": 3,"duration": 70},
            {"name": "Бургер комбо",     "emoji": "🍔",   "price": 16500, "category": "main", "desc": "Бүрэн иж бүрдэл","buff": "xp_boost","xp_mult": 3,"duration": 80},
            {"name": "Нэрийн цуйван",    "emoji": "🍝",   "price": 14000, "category": "main", "desc": "Монгол амт","buff": "xp_boost","xp_mult": 3,"duration": 80},
            {"name": "Пепперони пицца",  "emoji": "🍕",   "price": 28000, "category": "main", "desc": "Итали тансаг","buff": "xp_boost","xp_mult": 4,"duration": 90},
            {"name": "Шарсан хавирга",   "emoji": "🥩",   "price": 35000, "category": "main", "desc": "Шарсан махны дээж","buff": "xp_boost","xp_mult": 5,"duration": 120},
            {"name": "Будаатай карри",   "emoji": "🍛",   "price": 13000, "category": "main", "desc": "Энэтхэг амт","buff": "xp_boost","xp_mult": 2.8,"duration": 65},
            {"name": "Тако",             "emoji": "🌮",   "price": 11000, "category": "main", "desc": "Мексик гудамжны хоол","buff": "xp_boost","xp_mult": 2.5,"duration": 55},
        ]
        self.active_buffs = {}

    @commands.hybrid_command(name='cafe', description='Кафе цэс харж, хоол захиалах')
    @app_commands.guild_only()
    async def cafe(self, ctx: commands.Context):
        await ctx.defer()
        economy = self.bot.get_cog("Economy")
        if economy and await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            embed = discord.Embed(title="🚔 Шорон", description="Шоронд хоол захиалах боломжгүй.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="☕ Gurten | LGC – Кафе",
            description="Цэснээс хоолоо сонгон, хямд үнээр амттай хоол идэж, түр хугацааны buff аваарай!",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        drinks = [item for item in self.menu if item.get("category") == "drink"]
        snacks = [item for item in self.menu if item.get("category") == "snack"]
        mains = [item for item in self.menu if item.get("category") == "main"]

        if drinks:
            embed.add_field(name="🥤 Уух зүйлс", value="\n".join(f"{d['emoji']} **{d['name']}** — {d['price']:,}₮" for d in drinks), inline=False)
        if snacks:
            embed.add_field(name="🍟 Зууш / Амттан", value="\n".join(f"{s['emoji']} **{s['name']}** — {s['price']:,}₮" for s in snacks), inline=False)
        if mains:
            embed.add_field(name="🍔 Үндсэн хоол", value="\n".join(f"{m['emoji']} **{m['name']}** — {m['price']:,}₮" for m in mains), inline=False)

        embed.set_footer(text="Доорх унадаг цэснээс хоол сонгоод, идэхдээ g!dine <дугаар> командыг ашиглана уу.")
        view = CafeView(ctx, self)
        view.message = await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name='dine', description='Инвентариас хоол идэж buff авах')
    @app_commands.guild_only()
    async def dine(self, ctx: commands.Context, number: int):
        await ctx.defer()
        idx = number - 1
        if idx < 0 or idx >= len(self.menu):
            embed = discord.Embed(title="❌ Буруу дугаар", description="`/cafe` командаар дугаарыг харна уу.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        shop_cog = self.bot.get_cog("ShopCog")
        if not shop_cog:
            embed = discord.Embed(title="❌ Системийн алдаа", description="Дэлгүүрийн систем ажиллахгүй байна.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        food_id = 6000 + idx
        inv = await shop_cog.get_user_inventory(ctx.author.id, ctx.guild.id)
        if inv.get(food_id, 0) == 0:
            embed = discord.Embed(title="❌ Хоол байхгүй", description="Эхлээд `/cafe`-с худалдаж авна уу.", color=ERROR_COLOR)
            return await ctx.send(embed=embed)

        # Хоолыг инвентариас хасах
        await shop_cog.remove_item(ctx.author.id, ctx.guild.id, food_id, 1)

        # 🔗 Даалгаврын системд мэдэгдэх
        quests_cog = self.bot.get_cog("Quests")
        if quests_cog:
            await quests_cog.trigger_event(ctx.author.id, ctx.guild.id, "cafe_eat", 1)

        item = self.menu[idx]
        key = f"{ctx.author.id}_{ctx.guild.id}"
        end_time = time.time() + item['duration']
        self.active_buffs[key] = {
            "type": item['buff'],
            "end_time": end_time,
            "xp_mult": item.get('xp_mult', 1),
            "money_mult": item.get('money_mult', 1),
        }

        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            cat = item.get("category", "main")
            if cat == "drink":
                hunger_dec, mood_dec = 10, 10
            elif cat == "snack":
                hunger_dec, mood_dec = 20, 15
            else:
                hunger_dec, mood_dec = 40, 25
            new_hunger = max(0, hunger - hunger_dec)
            new_mood = max(0, mood - mood_dec)
            await economy.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=new_hunger, mood=new_mood)

            embed = discord.Embed(
                title="🍽️ Хоол идлээ!",
                description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** идэж дууслаа.\n"
                            f"✨ {item['buff']} идэвхжлээ ({item['duration']} сек)",
                color=SUCCESS_COLOR
            )
            embed.add_field(name="🍔 Өлсгөлөн", value=f"{hunger} → {new_hunger}/100 (-{hunger_dec})", inline=True)
            embed.add_field(name="😊 Уур", value=f"{mood} → {new_mood}/100 (-{mood_dec})", inline=True)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="🍽️ Хоол идлээ!",
                description=f"{ctx.author.mention} **{item['emoji']} {item['name']}** идэж дууслаа.\n"
                            f"✨ {item['buff']} идэвхжлээ ({item['duration']} сек)",
                color=SUCCESS_COLOR
            )
            await ctx.send(embed=embed)

    def get_buff(self, user_id, guild_id):
        key = f"{user_id}_{guild_id}"
        buff = self.active_buffs.get(key)
        if buff and time.time() > buff['end_time']:
            del self.active_buffs[key]
            return None
        return buff

async def setup(bot):
    await bot.add_cog(Cafe(bot))
