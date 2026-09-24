"""Aether Cafe: anime-themed food shop and temporary buffs."""

import time

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Select, View

CAFE_GOLD = 0xffc857
CAFE_PINK = 0xff4fa3
CAFE_ERROR = 0xff7aa8


class CafeView(View):
    def __init__(self, ctx, cafe):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cafe = cafe
        options = [
            discord.SelectOption(
                label=f"{item['emoji']} {item['name']} — {item['price']:,}₮",
                value=str(index),
                description=item['desc'][:100],
            )
            for index, item in enumerate(cafe.menu[:25])
        ]
        select = Select(placeholder="🍽️ Moonlit menu-с сонгоно уу...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message("❌ Энэ menu таных биш.", ephemeral=True)
        item = self.cafe.menu[int(self.children[0].values[0])]
        economy = self.ctx.bot.get_cog("Economy")
        if not economy:
            return await interaction.response.send_message("❌ Economy систем ачаалагдаагүй.", ephemeral=True)
        guild_id = self.ctx.guild.id
        if await economy.is_in_prison(interaction.user.id, guild_id):
            return await interaction.response.send_message("🚔 Шоронд байхдаа захиалга хийх боломжгүй.", ephemeral=True)
        balance = await economy.get_balance(interaction.user.id, guild_id)
        if balance < item["price"]:
            return await interaction.response.send_message(
                f"💸 Мөнгө хүрэхгүй байна. Үлдэгдэл: **{balance:,}₮**", ephemeral=True
            )
        await interaction.response.defer()
        await economy.update_balance(interaction.user.id, guild_id, -item["price"])
        self.cafe.active_buffs[f"{interaction.user.id}_{guild_id}"] = {
            "type": item["buff"],
            "end_time": time.time() + item["duration"],
            "xp_mult": item.get("xp_mult", 1),
            "money_mult": item.get("money_mult", 1),
        }
        shop = self.ctx.bot.get_cog("ShopCog")
        if shop:
            await shop.add_item(interaction.user.id, guild_id, 6000 + self.cafe.menu.index(item), 1)
        quests = self.ctx.bot.get_cog("Quests")
        if quests and hasattr(quests, "trigger_event"):
            await quests.trigger_event(interaction.user.id, guild_id, "cafe_purchase", 1)
        embed = discord.Embed(
            title="🌙 注文完了 — Moonlit Café",
            description=f"{item['emoji']} **{item['name']}** бэлэн боллоо!\n"
                        f"✨ Buff: `{item['duration']} секунд` · `x{item.get('xp_mult', 1)}`",
            color=CAFE_PINK,
        )
        await interaction.message.edit(embed=embed, view=None)


class Cafe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_buffs = {}
        self.menu = [
            {"name": "Sakura Latte", "emoji": "🌸☕", "price": 6500, "desc": "Сакурагийн зөөлөн амт", "buff": "xp_boost", "xp_mult": 1.5, "duration": 1800},
            {"name": "Moon Mochi", "emoji": "🌙🍡", "price": 8000, "desc": "Сарны гэрэлтэй амттан", "buff": "xp_boost", "xp_mult": 2, "duration": 2400},
            {"name": "Spirit Ramen", "emoji": "🍜", "price": 12000, "desc": "Quest хийх эрч хүч", "buff": "xp_boost", "xp_mult": 2.5, "duration": 3000},
            {"name": "Lightning Soda", "emoji": "⚡🥤", "price": 10000, "desc": "Аянга шиг сэргээно", "buff": "work_mult", "money_mult": 2, "duration": 1800},
            {"name": "Star Parfait", "emoji": "⭐🍨", "price": 15000, "desc": "Оддын онцгой dessert", "buff": "xp_boost", "xp_mult": 3, "duration": 3600},
        ]

    @commands.hybrid_command(name="cafe", description="Anime cafe-ийн menu харах, хоол захиалах")
    @app_commands.guild_only()
    async def cafe(self, ctx: commands.Context):
        economy = self.bot.get_cog("Economy")
        if economy and await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            return await ctx.send(embed=discord.Embed(title="🚔 Quest locked", description="Шоронд байхдаа cafe орох боломжгүй.", color=CAFE_ERROR))
        embed = discord.Embed(title="🌸 AETHER MOONLIT CAFÉ", description="Сонголтоо хийж түр хугацааны anime buff аваарай.", color=CAFE_GOLD)
        embed.add_field(name="📜 Menu", value="\n".join(f"{x['emoji']} **{x['name']}** — {x['price']:,}₮" for x in self.menu), inline=False)
        embed.set_footer(text="Доорх menu-с сонгоно уу • `A!dine <дугаар>`-аар иднэ")
        await ctx.send(embed=embed, view=CafeView(ctx, self))

    @commands.hybrid_command(name="dine", description="Cafe-ээс авсан хоол идэж buff авах")
    @app_commands.guild_only()
    async def dine(self, ctx: commands.Context, number: int):
        if not 1 <= number <= len(self.menu):
            return await ctx.send("❌ Menu-ийн зөв дугаар сонгоно уу.")
        shop = self.bot.get_cog("ShopCog")
        if not shop:
            return await ctx.send("❌ Inventory систем ачаалагдаагүй.")
        item = self.menu[number - 1]
        inventory = await shop.get_user_inventory(ctx.author.id, ctx.guild.id)
        food_id = 6000 + number - 1
        if inventory.get(food_id, 0) <= 0:
            return await ctx.send("🍽️ Энэ хоол inventory-д алга. Эхлээд `/cafe`-с аваарай.")
        await shop.remove_item(ctx.author.id, ctx.guild.id, food_id, 1)
        self.active_buffs[f"{ctx.author.id}_{ctx.guild.id}"] = {"type": item["buff"], "end_time": time.time() + item["duration"], "xp_mult": item.get("xp_mult", 1), "money_mult": item.get("money_mult", 1)}
        economy = self.bot.get_cog("Economy")
        if economy:
            hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
            category = item.get("category", "main")
            hunger_drop, mood_drop = {"drink": (10, 10), "snack": (20, 15), "main": (40, 25)}.get(category, (20, 15))
            await economy.set_hunger_mood(ctx.author.id, ctx.guild.id, hunger=max(0, hunger - hunger_drop), mood=max(0, mood - mood_drop))
        quests = self.bot.get_cog("Quests")
        if quests and hasattr(quests, "trigger_event"):
            await quests.trigger_event(ctx.author.id, ctx.guild.id, "cafe_eat", 1)
        await ctx.send(embed=discord.Embed(title="🍽️ 頂きます — Buff идэвхжлээ!", description=f"{item['emoji']} **{item['name']}** · `{item['duration']} секунд` · `x{item.get('xp_mult', 1)}`", color=CAFE_PINK))

    def get_buff(self, user_id, guild_id):
        key = f"{user_id}_{guild_id}"
        buff = self.active_buffs.get(key)
        if buff and time.time() >= buff["end_time"]:
            self.active_buffs.pop(key, None)
            return None
        return buff


async def setup(bot):
    await bot.add_cog(Cafe(bot))
