from utils.constants import EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
import discord
from discord.ext import commands
from discord import app_commands, ui
import time
import logging

logger = logging.getLogger(__name__)

SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
INFO_COLOR = 0x89b4fa


# ==================== ТУСЛАХ VIEW, MODAL ====================
class ConfirmView(ui.View):
    """Худалдаж авах, цуцлах үеийн баталгаажуулалт"""
    def __init__(self, timeout=60):
        super().__init__(timeout=timeout)
        self.value = None

    @ui.button(label="Тийм ✅", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: ui.Button):
        self.value = True
        self.stop()
        await interaction.response.defer()

    @ui.button(label="Үгүй ❌", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        self.value = False
        self.stop()
        await interaction.response.defer()


class SellModal(ui.Modal, title="📢 Бараа зарах"):
    price = ui.TextInput(label="Нэг ширхэгийн үнэ (₮)", placeholder="5000", required=True)
    quantity = ui.TextInput(label="Тоо хэмжээ", placeholder="1", default="1", required=True)

    def __init__(self, cog, item_id, item_name, item_emoji, available_qty, original_inter):
        super().__init__()
        self.cog = cog                     # Marketplace instance
        self.item_id = item_id
        self.item_name = item_name
        self.item_emoji = item_emoji
        self.available_qty = available_qty
        self.original_inter = original_inter

    async def on_submit(self, interaction: discord.Interaction):
        try:
            price = int(self.price.value)
            qty = int(self.quantity.value)
            if price <= 0 or qty <= 0 or qty > self.available_qty:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message(
                f"❌ Буруу утга. Үнэ эерэг, тоо 1-{self.available_qty} хооронд байх ёстой.",
                ephemeral=True
            )
        # Marketplace-ийн process_sell руу шилжүүлнэ
        await self.cog.process_sell(self.original_inter, self.item_id, qty, price)


class SearchModal(ui.Modal, title="🔍 Бараа хайх"):
    item_id = ui.TextInput(label="Барааны ID", placeholder="Барааны ID дугаар оруулна уу", required=True)

    def __init__(self, cog, original_inter):
        super().__init__()
        self.cog = cog
        self.original_inter = original_inter

    async def on_submit(self, interaction: discord.Interaction):
        try:
            item_id = int(self.item_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ ID нь тоо байх ёстой.", ephemeral=True)
        await self.cog.show_search_results(self.original_inter, item_id)


# ==================== MARKETPLACE COG ====================
class Marketplace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

    # ================== DB удирдлага ==================
    async def get_listing(self, listing_id: int):
        return await self.bot.db_manager.fetch_one("marketplace_listings", {"id": listing_id})

    async def delete_listing(self, listing_id: int):
        await self.bot.db_manager.delete("marketplace_listings", {"id": listing_id})

    async def get_all_listings(self, guild_id: int, page=0, per_page=5):
        offset = page * per_page
        return await self.bot.db_manager.fetch_all(
            "marketplace_listings",
            {"guild_id": str(guild_id)},
            order_by="created_at",
            desc=True,
            limit=per_page,
            offset=offset,
        )

    async def get_user_listings(self, guild_id: int, user_id: int):
        return await self.bot.db_manager.fetch_all(
            "marketplace_listings",
            {"guild_id": str(guild_id), "seller_id": str(user_id)},
            order_by="created_at",
            desc=True,
        )

    async def create_listing(self, guild_id: int, seller_id: int, item_id: int, quantity: int, price_per_item: int):
        now = int(time.time())
        result = await self.bot.db_manager.insert("marketplace_listings", {
            "guild_id": str(guild_id),
            "seller_id": str(seller_id),
            "item_id": item_id,
            "quantity": quantity,
            "price_per_item": price_per_item,
            "created_at": now,
        })
        return result[0].get("id") if result else None

    # ================== Туслах когууд ==================
    async def get_shop_cog(self):
        return self.bot.get_cog("ShopCog")

    async def get_economy_cog(self):
        return self.bot.get_cog("Economy")

    async def get_quests_cog(self):
        return self.bot.get_cog("Quests")

    # ================== ҮНДСЭН ҮЙЛДЛҮҮД ==================
    async def process_sell(self, interaction: discord.Interaction, item_id: int, quantity: int, price: int):
        """Барааны зарыг үүсгэх"""
        shop = await self.get_shop_cog()
        economy = await self.get_economy_cog()
        if not shop or not economy:
            return await interaction.followup.send("❌ Систем ажиллахгүй байна.", ephemeral=True)

        removed = await shop.remove_item(interaction.user.id, interaction.guild_id, item_id, quantity)
        if not removed:
            return await interaction.followup.send("❌ Барааг хасаж чадсангүй.", ephemeral=True)

        listing_id = await self.create_listing(interaction.guild_id, interaction.user.id, item_id, quantity, price)

        item = await shop.get_item(item_id)
        item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"

        embed = discord.Embed(
            title="✅ ЗАР ҮҮСГЭЛЭЭ",
            description=f"{interaction.user.mention} таны бараа зах дээр гарлаа!\n\n"
                        f"{item_str} x{quantity}\n"
                        f"💰 Үнэ: {price:,}₮/ш (Нийт: {price*quantity:,}₮)\n"
                        f"🆔 Зарлалын ID: `{listing_id}`",
            color=SUCCESS_COLOR
        )
        embed.set_footer(text="Бусад хэрэглэгчид энэ ID-аар худалдаж авах боломжтой")
        await interaction.followup.send(embed=embed, ephemeral=False)

        quests_cog = await self.get_quests_cog()
        if quests_cog:
            await quests_cog.trigger_event(interaction.user.id, interaction.guild_id, "trade_complete", 1)

    async def show_search_results(self, interaction: discord.Interaction, item_id: int):
        """Хайлтын үр дүнг харуулах"""
        rows = await self.bot.db_manager.fetch_all(
            "marketplace_listings",
            {"guild_id": str(interaction.guild_id), "item_id": item_id},
            order_by="price_per_item",
            limit=10,
        )
        rows = [
            (r["id"], r["seller_id"], r["quantity"], r["price_per_item"], r["created_at"])
            for r in rows
        ]

        if not rows:
            return await interaction.followup.send(
                f"📭 `{item_id}` ID-тай барааны идэвхтэй зарлал байхгүй.", ephemeral=True
            )

        shop = await self.get_shop_cog()
        item = await shop.get_item(item_id) if shop else None
        item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"

        embed = discord.Embed(title=f"🔍 {item_str} ЗАРЛАЛУУД", color=GOLD_COLOR)
        for lid, seller_id, qty, price, _ in rows:
            seller = interaction.guild.get_member(int(seller_id))
            seller_name = seller.display_name if seller else "Тодорхойгүй"
            embed.add_field(
                name=f"📌 ID: {lid} | {seller_name}",
                value=f"x{qty} → {price:,}₮/ш (Нийт: {price*qty:,}₮)",
                inline=False
            )
        embed.set_footer(text="Худалдаж авах: /marketplace buy <ID> эсвэл самбараас сонго")
        await interaction.followup.send(embed=embed, ephemeral=False)

    # ================== ГОЛ ИНТЕРАКТИВ САМБАР ==================
    class MainView(ui.View):
        def __init__(self, cog, ctx):
            super().__init__(timeout=300)
            self.cog = cog
            self.ctx = ctx
            self.message = None

        @ui.button(label="📢 Зарах", style=discord.ButtonStyle.primary, emoji="🏷️")
        async def sell_btn(self, interaction: discord.Interaction, button: ui.Button):
            shop = await self.cog.get_shop_cog()
            if not shop:
                return await interaction.response.send_message("❌ Дэлгүүрийн систем ачаалагдаагүй.", ephemeral=True)

            inv = await shop.get_user_inventory(interaction.user.id, interaction.guild_id)
            if not inv:
                return await interaction.response.send_message("❌ Танд зарагдах бараа байхгүй.", ephemeral=True)

            options = []
            for item_id, qty in inv.items():
                item = await shop.get_item(item_id)
                if not item:
                    continue
                label = f"{item['emoji']} {item['name']} (x{qty})"
                options.append(discord.SelectOption(label=label[:100], value=str(item_id), description=f"ID:{item_id}"))

            if not options:
                return await interaction.response.send_message("❌ Зарагдах бараа олдсонгүй.", ephemeral=True)

            options = options[:25]
            view = ui.View(timeout=180)
            select = ui.Select(placeholder="📦 Зарах бараагаа сонго...", options=options)

            async def select_cb(sel_inter: discord.Interaction):
                item_id = int(select.values[0])
                item = await shop.get_item(item_id)
                if not item:
                    return await sel_inter.response.send_message("❌ Бараа олдсонгүй.", ephemeral=True)
                qty = inv[item_id]
                modal = SellModal(self.cog, item_id, item['name'], item['emoji'], qty, sel_inter)
                await sel_inter.response.send_modal(modal)

            select.callback = select_cb
            view.add_item(select)
            await interaction.response.send_message("📦 Зарах бараагаа сонгоно уу:", view=view, ephemeral=True)

        @ui.button(label="🛒 Худалдаж авах", style=discord.ButtonStyle.success)
        async def buy_btn(self, interaction: discord.Interaction, button: ui.Button):
            await self.cog.show_listings(interaction, page=0)

        @ui.button(label="📋 Миний зарууд", style=discord.ButtonStyle.secondary)
        async def my_listings_btn(self, interaction: discord.Interaction, button: ui.Button):
            await self.cog.show_my_listings(interaction)

        @ui.button(label="🔍 Хайх", style=discord.ButtonStyle.blurple)
        async def search_btn(self, interaction: discord.Interaction, button: ui.Button):
            modal = SearchModal(self.cog, interaction)
            await interaction.response.send_modal(modal)

    # ================== ХУДАЛДАЖ АВАХ (ХУУДАСЛАЛТТАЙ) ==================
    async def show_listings(self, interaction: discord.Interaction, page: int = 0):
        rows = await self.get_all_listings(interaction.guild_id, page=page, per_page=5)
        if not rows:
            embed = discord.Embed(title="🛒 ЗАХ ЗЭЭЛ", description="Одоохондоо идэвхтэй зарлал байхгүй.", color=INFO_COLOR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        shop = await self.get_shop_cog()
        view = self.ListingsView(self, interaction.user.id, page)
        embed = view.build_embed(rows, shop, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

    class ListingsView(ui.View):
        def __init__(self, cog, buyer_id, page):
            super().__init__(timeout=180)
            self.cog = cog
            self.buyer_id = buyer_id
            self.page = page
            self.selected_listing_id = None

        async def update_embed(self, interaction: discord.Interaction):
            rows = await self.cog.get_all_listings(interaction.guild_id, page=self.page, per_page=5)
            shop = await self.cog.get_shop_cog()
            embed = self.build_embed(rows, shop, interaction.guild)
            self._refresh_buttons(rows)
            await interaction.response.edit_message(embed=embed, view=self)

        def build_embed(self, rows, shop, guild):
            embed = discord.Embed(title="🛒 ИДЭВХТЭЙ ЗАРЛАЛУУД", color=GOLD_COLOR)
            if not rows:
                embed.description = "Одоохондоо зарлал байхгүй."
                return embed
            for lid, seller_id, item_id, qty, price, _ in rows:
                item = shop.get_item(item_id) if shop else None
                item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"
                seller = guild.get_member(int(seller_id))
                seller_name = seller.display_name if seller else "Тодорхойгүй"
                embed.add_field(
                    name=f"📌 #{lid} | {seller_name}",
                    value=f"{item_str} x{qty}\n💰 {price:,}₮/ш (Нийт: {price*qty:,}₮)",
                    inline=False
                )
            embed.set_footer(text=f"Хуудас {self.page+1}")
            return embed

        def _refresh_buttons(self, rows):
            self.clear_items()
            # Select
            options = []
            for lid, seller_id, item_id, qty, price, _ in rows:
                shop = self.cog.bot.get_cog("ShopCog")
                item = shop.get_item(item_id) if shop else None
                item_name = item['name'] if item else f"ID:{item_id}"
                label = f"#{lid} {item_name[:20]} x{qty} {price:,}₮"
                options.append(discord.SelectOption(label=label[:100], value=str(lid)))
            if options:
                select = ui.Select(placeholder="📦 Худалдаж авах бараагаа сонго...", options=options)
                select.callback = self.select_listing
                self.add_item(select)

            # Buy button
            buy_btn = ui.Button(label="✅ Худалдаж авах", style=discord.ButtonStyle.green, disabled=True)
            buy_btn.callback = self.buy_selected
            self.buy_btn = buy_btn
            self.add_item(buy_btn)

            # Pagination
            prev_btn = ui.Button(label="◀ Өмнөх", style=discord.ButtonStyle.gray, disabled=self.page == 0)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)

            next_btn = ui.Button(label="Дараах ▶", style=discord.ButtonStyle.gray)
            next_btn.callback = self.next_page
            self.add_item(next_btn)

        async def select_listing(self, interaction: discord.Interaction):
            self.selected_listing_id = int(interaction.data['values'][0])
            self.buy_btn.disabled = False
            await interaction.response.edit_message(view=self)

        async def buy_selected(self, interaction: discord.Interaction):
            if self.selected_listing_id is None:
                return await interaction.response.send_message("❌ Эхлээд бараа сонгоно уу.", ephemeral=True)

            listing = await self.cog.get_listing(self.selected_listing_id)
            if not listing:
                return await interaction.response.send_message("❌ Зарлал олдсонгүй.", ephemeral=True)

            gid, seller_id, item_id, quantity, price_per_item, _ = listing
            if int(gid) != interaction.guild_id:
                return await interaction.response.send_message("❌ Энэ зарлал энэ серверт хамаарахгүй.", ephemeral=True)
            if str(seller_id) == str(interaction.user.id):
                return await interaction.response.send_message("❌ Өөрийн зарыг худалдаж болохгүй.", ephemeral=True)

            total_price = price_per_item * quantity
            economy = await self.cog.get_economy_cog()
            balance = await economy.get_balance(interaction.user.id, interaction.guild_id)
            if balance < total_price:
                return await interaction.response.send_message(
                    f"❌ Мөнгө хүрэлцэхгүй. Хэрэгтэй: {total_price:,}₮, Таны үлдэгдэл: {balance:,}₮",
                    ephemeral=True
                )

            shop = await self.cog.get_shop_cog()
            item = await shop.get_item(item_id)
            item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"

            embed = discord.Embed(
                title="🛒 ХУДАЛДАН АВАХ",
                description=f"Та {item_str} x{quantity} -г **{total_price:,}₮**-өөр худалдаж авах уу?",
                color=WARNING_COLOR
            )
            confirm_view = ConfirmView()
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
            await confirm_view.wait()
            if confirm_view.value is not True:
                return await interaction.followup.send("❌ Худалдан авалт цуцлагдлаа.", ephemeral=True)

            # Гүйлгээ
            await economy.update_balance(interaction.user.id, interaction.guild_id, -total_price)
            await economy.update_balance(int(seller_id), interaction.guild_id, total_price)
            await shop.add_item(interaction.user.id, interaction.guild_id, item_id, quantity)
            await self.cog.delete_listing(self.selected_listing_id)

            success_embed = discord.Embed(
                title="✅ ХУДАЛДАН АВАЛТ АМЖИЛТТАЙ",
                description=f"{interaction.user.mention} {item_str} x{quantity} -г {total_price:,}₮-өөр авлаа.",
                color=SUCCESS_COLOR
            )
            await interaction.followup.send(embed=success_embed)

            seller_member = interaction.guild.get_member(int(seller_id))
            if seller_member:
                try: await seller_member.send(f"✅ Таны {item_str} x{quantity} зарагдлаа! +{total_price:,}₮")
                except: pass

            quests_cog = await self.cog.get_quests_cog()
            if quests_cog:
                await quests_cog.trigger_event(interaction.user.id, interaction.guild_id, "trade_complete", 1)

            await self.update_embed(interaction)

        async def prev_page(self, interaction: discord.Interaction):
            self.page = max(0, self.page - 1)
            await self.update_embed(interaction)

        async def next_page(self, interaction: discord.Interaction):
            self.page += 1
            await self.update_embed(interaction)

    # ================== МИНИЙ ЗАРУУД ==================
    async def show_my_listings(self, interaction: discord.Interaction):
        rows = await self.get_user_listings(interaction.guild_id, interaction.user.id)
        if not rows:
            embed = discord.Embed(title="📋 Миний зарууд", description="Танд идэвхтэй зарлал байхгүй.", color=INFO_COLOR)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        shop = await self.get_shop_cog()
        view = ui.View(timeout=180)
        embed = discord.Embed(title="📋 ТАНЫ ИДЭВХТЭЙ ЗАРУУД", color=GOLD_COLOR)
        for lid, item_id, qty, price, _ in rows:
            item = shop.get_item(item_id) if shop else None
            item_str = f"{item['emoji']} **{item['name']}**" if item else f"ID:{item_id}"
            embed.add_field(
                name=f"📌 #{lid}",
                value=f"{item_str} x{qty} → {price:,}₮/ш",
                inline=False
            )
            if len(view.children) < 5:
                btn = ui.Button(label=f"❌ #{lid} цуцлах", style=discord.ButtonStyle.red)
                btn.callback = self.make_cancel_callback(lid)
                view.add_item(btn)

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def make_cancel_callback(self, listing_id: int):
        async def cancel_cb(interaction: discord.Interaction):
            listing = await self.get_listing(listing_id)
            if not listing or str(listing[2]) != str(interaction.user.id):
                return await interaction.response.send_message("❌ Та зөвхөн өөрийн зарыг цуцлах боломжтой.", ephemeral=True)
            shop = await self.get_shop_cog()
            item_id = listing[3]
            qty = listing[4]
            await shop.add_item(interaction.user.id, interaction.guild_id, item_id, qty)
            await self.delete_listing(listing_id)
            await interaction.response.send_message(f"✅ #{listing_id} зар цуцлагдлаа. Бараа инвентарт буцлаа.", ephemeral=True)
            await self.show_my_listings(interaction)
        return cancel_cb

    # ================== КОМАНДУУД ==================
    @commands.hybrid_command(name='market', description="Зах зээлийн интерактив самбар нээх")
    async def market_panel(self, ctx):
        embed = discord.Embed(
            title="🛒 ЗАХ ЗЭЭЛ",
            description="Доорх товчнуудыг ашиглан бараа зарж, худалдаж авах боломжтой.",
            color=GOLD_COLOR
        )
        view = self.MainView(self, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg

    # Слаш командууд (самбар луу хөтлөх)
    marketplace_group = app_commands.Group(name="marketplace", description="Зах зээлийн удирдлага (слаш)")

    @marketplace_group.command(name="panel", description="Интерактив самбар нээх")
    async def marketplace_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🛒 ЗАХ ЗЭЭЛ",
            description="Доорх товчнуудыг ашиглан бараа зарж, худалдаж авах боломжтой.",
            color=GOLD_COLOR
        )
        view = self.MainView(self, interaction)
        await interaction.response.send_message(embed=embed, view=view)
        view.message = await interaction.original_response()

    @commands.hybrid_command(name='mp', description="Зах зээлийн тусламж")
    async def mp_help(self, ctx):
        embed = discord.Embed(
            title="🛒 ЗАХ ЗЭЭЛ",
            description="**Командууд:**\n"
                        "`/marketplace panel` – интерактив самбар\n"
                        "`/marketplace buy <ID>` – худалдаж авах\n"
                        "`/marketplace sell` – бараа зарах\n"
                        "`/marketplace listings [page]` – жагсаалт\n"
                        "`/marketplace cancel <ID>` – цуцлах\n"
                        "`/marketplace search <item_id>` – хайх",
            color=GOLD_COLOR
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Marketplace(bot))