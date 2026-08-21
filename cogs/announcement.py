import discord
from discord.ext import commands
from discord import app_commands, ui
from typing import Optional

# ══════════════ ӨНГӨНИЙ СОНГОЛТ ══════════════
COLOR_CHOICES = {
    "🟢 Ногоон": 0x57f287,
    "🔴 Улаан": 0xed4245,
    "🔵 Хөх": 0x3498db,
    "🟡 Шар": 0xfee75c,
    "🟣 Ягаан": 0xcba6f7,
    "⚪ Саарал": 0x6c7086,
    "🟠 Улбар шар": 0xfab387,
}

# ══════════════ МОДАЛУУД ══════════════
class TitleModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Гарчиг оруулах")
        self.view = view
        self.add_item(ui.TextInput(
            label="Зарлалын гарчиг",
            placeholder="Жишээ: Чухал мэдэгдэл!",
            max_length=256,
            required=True,
            custom_id="title_input",
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.view.title = self.get_item("title_input").value
        await interaction.response.send_message(f"✅ Гарчиг тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)


class DescriptionModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Тайлбар оруулах")
        self.view = view
        self.add_item(ui.TextInput(
            label="Зарлалын тайлбар",
            style=discord.TextStyle.paragraph,
            placeholder="Дэлгэрэнгүй мэдээлэл...",
            max_length=4000,
            required=True,
            custom_id="description_input",
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.view.description = self.get_item("description_input").value
        await interaction.response.send_message(f"✅ Тайлбар тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)


class ImageModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Зураг оруулах")
        self.view = view
        self.add_item(ui.TextInput(
            label="Зургийн URL (хоосон орхивол зураггүй)",
            placeholder="https://i.imgur.com/...",
            required=False,
            custom_id="image_input",
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.view.image_url = self.get_item("image_input").value.strip() or None
        await interaction.response.send_message(f"✅ Зураг тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)


class FooterModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Footer текст оруулах")
        self.view = view
        self.add_item(ui.TextInput(
            label="Footer текст (хоосон орхивол footer-гүй)",
            placeholder="Зарлалын төгсгөлд харагдах текст",
            required=False,
            custom_id="footer_input",
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.view.footer = self.get_item("footer_input").value.strip() or None
        await interaction.response.send_message(f"✅ Footer тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)


class MentionModal(ui.Modal):
    def __init__(self, view):
        super().__init__(title="Хэрэглэгч/Роль дуудах")
        self.view = view
        self.add_item(ui.TextInput(
            label="ID (хоосон орхивол дуудахгүй)",
            placeholder="Роль эсвэл хэрэглэгчийн ID",
            required=False,
            custom_id="mention_input",
        ))

    async def on_submit(self, interaction: discord.Interaction):
        self.view.mention = self.get_item("mention_input").value.strip() or None
        await interaction.response.send_message(f"✅ Дуудах тохируулагдлаа.", ephemeral=True)
        await self.view.refresh(interaction)


# ══════════════ ҮНДСЭН САМБАР ══════════════
class AnnouncementView(ui.View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

        # Тохиргооны утгууд
        self.channel: Optional[discord.TextChannel] = None
        self.title: Optional[str] = None
        self.description: Optional[str] = None
        self.embed_color: int = 0x57f287
        self.image_url: Optional[str] = None
        self.footer: Optional[str] = None
        self.mention: Optional[str] = None
        self.thumbnail_url: Optional[str] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        embed = self.build_preview_embed()
        await interaction.edit_original_response(embed=embed, view=self)

    def build_preview_embed(self):
        color_name = next((k for k, v in COLOR_CHOICES.items() if v == self.embed_color), "Тодорхойгүй")
        embed = discord.Embed(
            title="📢 Зарлалын тохиргоо",
            description="Доорх товчнуудаар зарлалаа тохируулж, **Илгээх** товчоор зарлалаа илгээнэ үү.",
            color=0x2b2d31
        )
        embed.add_field(name="📢 Суваг", value=self.channel.mention if self.channel else "❌ Сонгогдоогүй", inline=True)
        embed.add_field(name="🎨 Өнгө", value=color_name, inline=True)
        embed.add_field(name="📝 Гарчиг", value=self.title or "❌ Оруулаагүй", inline=False)
        embed.add_field(name="📃 Тайлбар", value=(self.description[:200] + "..." if len(self.description or "") > 200 else self.description) or "❌ Оруулаагүй", inline=False)
        embed.add_field(name="🖼️ Зураг", value=self.image_url or "❌ Байхгүй", inline=True)
        embed.add_field(name="🔖 Footer", value=self.footer or "❌ Байхгүй", inline=True)
        embed.add_field(name="📣 Дуудах", value=self.mention or "❌ Байхгүй", inline=True)
        embed.set_footer(text="Урьдчилан харах embed доор харагдана.")

        # Хэрэв мэдээлэл хангалттай бол жинхэнэ embed-ийг харуулах
        if self.title and self.description:
            preview = discord.Embed(
                title=self.title,
                description=self.description,
                color=self.embed_color
            )
            if self.image_url:
                preview.set_image(url=self.image_url)
            if self.footer:
                preview.set_footer(text=self.footer)
            if self.thumbnail_url:
                preview.set_thumbnail(url=self.thumbnail_url)
            embed.set_image(url="attachment://preview_placeholder.png")  # Заавал биш, зүгээр л ялгах
            # Бид embed-ийг харуулахын тулд тусдаа мессеж болгох хэрэгтэй, 
            # гэхдээ энэ самбарт preview-г харуулах нь илүүц тул зүгээр л мэдээлэл харуулна.
        return embed

    # ---------- СУВАГ СОНГОХ ----------
    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Зарлал илгээх суваг сонго...", min_values=1, max_values=1, row=0)
    async def select_channel(self, interaction: discord.Interaction, select: ui.ChannelSelect):
        self.channel = select.values[0]
        await interaction.response.defer()
        await self.refresh(interaction)

    # ---------- ТОВЧНУУД ----------
    @ui.button(label="📝 Гарчиг", style=discord.ButtonStyle.primary, row=1)
    async def title_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TitleModal(self))

    @ui.button(label="📃 Тайлбар", style=discord.ButtonStyle.primary, row=1)
    async def description_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DescriptionModal(self))

    @ui.button(label="🎨 Өнгө", style=discord.ButtonStyle.secondary, row=1)
    async def color_button(self, interaction: discord.Interaction, button: ui.Button):
        # Өнгийг сонгох dropdown
        options = [discord.SelectOption(label=name, value=str(code)) for name, code in COLOR_CHOICES.items()]
        select = ui.Select(placeholder="Өнгө сонго...", options=options)

        async def color_callback(select_interaction: discord.Interaction):
            self.embed_color = int(select.values[0])
            await select_interaction.response.send_message(f"✅ Өнгө сонгогдлоо.", ephemeral=True)
            await self.refresh(interaction)

        select.callback = color_callback
        view = ui.View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message("Өнгө сонгоно уу:", view=view, ephemeral=True)

    @ui.button(label="🖼️ Зураг", style=discord.ButtonStyle.secondary, row=2)
    async def image_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ImageModal(self))

    @ui.button(label="🔖 Footer", style=discord.ButtonStyle.secondary, row=2)
    async def footer_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(FooterModal(self))

    @ui.button(label="📣 Дуудах", style=discord.ButtonStyle.secondary, row=2)
    async def mention_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(MentionModal(self))

    @ui.button(label="✅ ИЛГЭЭХ", style=discord.ButtonStyle.success, row=3)
    async def send_button(self, interaction: discord.Interaction, button: ui.Button):
        if not self.channel:
            return await interaction.response.send_message("❌ Сувгаа сонгоно уу.", ephemeral=True)
        if not self.title or not self.description:
            return await interaction.response.send_message("❌ Гарчиг болон тайлбараа оруулна уу.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        # Embed үүсгэх
        embed = discord.Embed(
            title=self.title,
            description=self.description,
            color=self.embed_color
        )
        if self.image_url:
            embed.set_image(url=self.image_url)
        if self.footer:
            embed.set_footer(text=self.footer)
        if self.thumbnail_url:
            embed.set_thumbnail(url=self.thumbnail_url)

        # Илгээх
        content = None
        if self.mention:
            try:
                mention_id = int(self.mention)
                # Энэ нь хэрэглэгч эсвэл роль байж болно
                content = f"<@&{mention_id}>" if interaction.guild.get_role(mention_id) else f"<@{mention_id}>"
            except ValueError:
                content = self.mention  # Түүхий текст

        await self.channel.send(content=content, embed=embed)
        await interaction.followup.send(f"✅ Зарлал {self.channel.mention} сувагт амжилттай илгээгдлээ!", ephemeral=True)

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        if self.message:
            for child in self.children:
                child.disabled = True
            try:
                await self.message.edit(view=self)
            except:
                pass


# ══════════════ COG ══════════════
class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announce", description="Зарлал үүсгэх самбар нээх")
    @app_commands.default_permissions(administrator=True)
    async def announce(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        view = AnnouncementView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_preview_embed()
        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = msg


async def setup(bot):
    await bot.add_cog(Announcement(bot))
