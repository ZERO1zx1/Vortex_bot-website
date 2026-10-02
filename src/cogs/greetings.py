import json
import logging
import random
from dataclasses import dataclass
from urllib.parse import urlsplit

import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, Modal, TextInput, View

from src.utils.config_cache import ConfigCache

logger = logging.getLogger(__name__)

# ===== COLORS =====
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR   = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR    = 0xfab387
INFO_COLOR    = 0x89b4fa
PURPLE_COLOR  = 0xcba6f7

# ===== CONFIG DATACLASS =====
@dataclass
class GuildConfig:
    guild_id: int
    welcome_channel: int | None = None
    goodbye_channel: int | None = None
    boost_channel: int | None = None
    welcome_template_id: int | None = None
    goodbye_template_id: int | None = None
    boost_template_id: int | None = None
    welcome_enabled: bool = True
    goodbye_enabled: bool = True
    boost_enabled: bool = True
    dm_on_welcome: bool = False
    log_channel: int | None = None

    @property
    def is_welcome_active(self) -> bool:
        return self.welcome_channel is not None and self.welcome_enabled

    @property
    def is_goodbye_active(self) -> bool:
        return self.goodbye_channel is not None and self.goodbye_enabled

    @property
    def is_boost_active(self) -> bool:
        return self.boost_channel is not None and self.boost_enabled

# ===== DEFAULT TEMPLATES =====
DEFAULT_TEMPLATES = {
    "welcome": {
        "title": "✦ New Star Arrival — {user:name}",
        "description": (
            "🌸 **{server:name}** anime guild-д тавтай морил!\n"
            "Та манай **{server:members}** дахь шинэ гишүүн боллоо.\n\n"
            "📜 Дүрмээ уншаад, 💬 ерөнхий чатад өөрийгөө танилцуулаарай.\n"
            "*Таны anime story эндээс эхэлнэ.*"
        ),
        "color": 0x63D9FF,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Aether Guild • Anime Chronicle • {date}",
        "footer_icon": "{server:icon}",
        "buttons": [
            {"label": "📜 Дүрэм", "url": "https://discord.com/channels/...", "style": 5},
            {"label": "🌐 Вебсайт", "url": "https://example.com", "style": 5}
        ]
    },
    "goodbye": {
        "title": "🌙 Until Next Episode — {user:name}",
        "description": (
            "{user:mention} дараагийн адал явдал руугаа мордлоо.\n"
            "Guild-д **{server:members}** гишүүн үлдлээ.\n\n"
            "🌸 Зам тань үргэлж гэрэлтэй байх болтугай."
        ),
        "color": 0xC77DFF,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Aether Guild • Until we meet again • {date}",
        "footer_icon": "{server:icon}",
        "buttons": []
    },
    "boost": {
        "title": "✦ Starry Boost!",
        "description": (
            "{user:mention} guild-ийн оддыг улам тодрууллаа! ✨\n"
            "Маш их баярлалаа!\n\n"
            "Одоо сервер **{server:boost_level}** түвшинд хүрлээ!\n"
            "Нийт boost: **{server:boost_count}** 🌠"
        ),
        "color": 0xFF5C8A,
        "thumbnail": "{user:avatar}",
        "image": "",
        "author_name": "",
        "author_icon": "",
        "footer_text": "Aether Guild • Starry power awakened • {date}",
        "footer_icon": "{server:icon}",
        "buttons": []
    }
}

RANDOM_GREETINGS = [
    "Сайн байна уу! Тавтай морил!",
    "Таныг харсандаа баяртай байна!",
    "Манай серверт нэгдсэнд баярлалаа!",
    "Шинэ гишүүн маань ирлээ!",
    "Серверт тавтай морилно уу!",
]

PLACEHOLDERS = {
    "{user:mention}": "Хэрэглэгчийг дурдах (@Boldoo)",
    "{user:name}": "Discord нэр",
    "{user:display_name}": "Сервер дээрх нэр",
    "{user:id}": "ID дугаар",
    "{user:avatar}": "Профайл зургийн URL",
    "{user:created_at}": "Бүртгэл үүсгэсэн огноо",
    "{user:joined_at}": "Серверт нэгдсэн огноо",
    "{server:name}": "Серверийн нэр",
    "{server:id}": "Серверийн ID",
    "{server:members}": "Нийт гишүүдийн тоо",
    "{server:icon}": "Серверийн зургийн URL",
    "{server:owner}": "Эзэмшигчийн нэр",
    "{server:boost_count}": "Нийт boost тоо",
    "{server:boost_level}": "Boost түвшин",
    "{date}": "Одоогийн огноо",
    "{time}": "Одоогийн цаг",
    "{newline}": "Шинэ мөр",
    "{random:greeting}": "Санамсаргүй мэндчилгээ",
}

# ===== UI COMPONENTS =====
async def authorize_template_editor(
    interaction: discord.Interaction, guild_id: int, owner_id: int
) -> bool:
    """Recheck the editor's identity and current permissions on every UI action."""
    if (
        interaction.guild_id != guild_id
        or interaction.user.id != owner_id
        or not isinstance(interaction.user, discord.Member)
        or not interaction.permissions.manage_guild
    ):
        await interaction.response.send_message(
            "❌ Энэ засварлагчийг зөвхөн нээсэн серверийн эрхтэй хэрэглэгч ашиглана.",
            ephemeral=True,
        )
        return False
    return True


def valid_button_url(url: str) -> bool:
    if not isinstance(url, str):
        return False
    try:
        parsed = urlsplit(url)
        return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
    except ValueError:
        return False


class GreetingButtonModal(Modal):
    def __init__(self, callback_func):
        super().__init__(title="🔘 Товчлуур нэмэх")
        self.callback = callback_func
        self.label_input = TextInput(label="Товчны текст", placeholder="Жишээ: 📜 Дүрэм унших", required=True, max_length=80)
        self.add_item(self.label_input)
        self.url_input = TextInput(label="Товчны URL", placeholder="https://...", required=True, max_length=500)
        self.add_item(self.url_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.callback(interaction, self.label_input.value, self.url_input.value)

class TemplateCreateModal(Modal, title="📝 Embed Загвар бүтээх"):
    def __init__(
        self, cog, guild_id: int, owner_id: int,
        existing: dict | None = None, template_id: int | None = None,
    ):
        super().__init__()
        self.cog = cog
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.template_id = template_id
        self.existing = existing or {}
        self.template_name = TextInput(
            label="🏷️ Загварын нэр",
            placeholder="Жишээ: Миний Welcome загвар",
            required=True,
            max_length=100,
            default=self.existing.get("name", "")
        )
        self.title_input = TextInput(
            label="📌 Embed гарчиг",
            placeholder="Хувьсагч ашиглаж болно...",
            required=False,
            max_length=256,
            default=self.existing.get("title", "")
        )
        self.description_input = TextInput(
            label="📝 Embed тайлбар",
            style=discord.TextStyle.long,
            placeholder="Хувьсагч ашиглаж болно: {user}, {server:name}...",
            required=True,
            max_length=2000,
            default=self.existing.get("description", "")
        )
        color_default = f"#{self.existing['color']:06x}" if "color" in self.existing else ""
        self.color_input = TextInput(
            label="🎨 Өнгө (Hex)",
            placeholder="#57f287",
            required=False,
            max_length=7,
            default=color_default
        )
        self.thumbnail_input = TextInput(
            label="🖼️ Thumbnail URL",
            placeholder="Хувьсагч эсвэл URL...",
            required=False,
            max_length=500,
            default=self.existing.get("thumbnail", "")
        )
        self.add_item(self.template_name)
        self.add_item(self.title_input)
        self.add_item(self.description_input)
        self.add_item(self.color_input)
        self.add_item(self.thumbnail_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not await authorize_template_editor(interaction, self.guild_id, self.owner_id):
            return
        try:
            color = int(self.color_input.value.lstrip('#'), 16) if self.color_input.value else 0x57f287
        except ValueError:
            return await interaction.response.send_message("❌ Буруу Hex өнгө!", ephemeral=True)
        if not 0 <= color <= 0xFFFFFF:
            return await interaction.response.send_message("❌ Буруу Hex өнгө!", ephemeral=True)

        base = self.existing.copy() if self.existing else {}
        base.update({
            "name": self.template_name.value,
            "title": self.title_input.value,
            "description": self.description_input.value,
            "color": color,
            "thumbnail": self.thumbnail_input.value,
            "image": base.get("image", ""),
            "author_name": base.get("author_name", ""),
            "author_icon": base.get("author_icon", ""),
            "footer_text": base.get("footer_text", ""),
            "footer_icon": base.get("footer_icon", ""),
            "buttons": base.get("buttons", [])
        })
        await interaction.response.send_message(
            "✅ Загвар бэлэн боллоо! Товчлуур нэмээд хадгалах боломжтой.",
            view=ButtonAddView(base, self.guild_id, self.owner_id, self.cog, self.template_id),
            ephemeral=True
        )

class ButtonAddView(View):
    def __init__(
        self, template: dict, guild_id: int, owner_id: int, cog,
        template_id: int | None = None,
    ):
        super().__init__(timeout=300)
        self.template = template
        self.guild_id = guild_id
        self.owner_id = owner_id
        self.template_id = template_id
        self.cog = cog
        self.saved = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not await authorize_template_editor(interaction, self.guild_id, self.owner_id):
            return False
        if self.saved:
            await interaction.response.send_message("✅ Энэ загвар аль хэдийн хадгалагдсан.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔘 Товчлуур нэмэх", style=discord.ButtonStyle.primary)
    async def add_button(self, interaction: discord.Interaction, button: Button):
        modal = GreetingButtonModal(self.add_button_callback)
        await interaction.response.send_modal(modal)

    async def add_button_callback(self, interaction, label, url):
        if not await self.interaction_check(interaction):
            return
        if len(self.template["buttons"]) >= 25:
            return await interaction.response.send_message("❌ Дээд тал нь 25 товчлуур нэмнэ.", ephemeral=True)
        if not valid_button_url(url):
            return await interaction.response.send_message("❌ http:// эсвэл https:// URL оруулна уу.", ephemeral=True)
        self.template["buttons"].append({"label": label, "url": url, "style": 5})
        await interaction.response.send_message(f"✅ '{label}' товчлуур нэмэгдлээ!", ephemeral=True, view=self)

    @discord.ui.button(label="💾 Хадгалах", style=discord.ButtonStyle.success)
    async def save_template(self, interaction: discord.Interaction, button: Button):
        if not await self.interaction_check(interaction):
            return
        # Mark before the first await to prevent overlapping save button clicks.
        self.saved = True
        await interaction.response.defer(ephemeral=True)
        try:
            saved = await self.cog.save_template(
                self.guild_id, self.owner_id, self.template, template_id=self.template_id,
            )
        except Exception:
            self.saved = False
            logger.exception("Failed to save greeting template in guild %s", self.guild_id)
            await interaction.followup.send("❌ Загвар хадгалахад алдаа гарлаа.", ephemeral=True)
            return
        if not saved:
            self.saved = False
            await interaction.followup.send("❌ Загвар олдсонгүй эсвэл таны загвар биш байна.", ephemeral=True)
            return
        await interaction.followup.send("✅ Загвар амжилттай хадгалагдлаа!", ephemeral=True)
        self.stop()

class TemplateCreateView(View):
    def __init__(self, cog, guild_id: int, owner_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return await authorize_template_editor(interaction, self.guild_id, self.owner_id)

    @discord.ui.button(label="📝 Шинэ загвар бүтээх", style=discord.ButtonStyle.primary)
    async def create_new(self, interaction: discord.Interaction, button: Button):
        modal = TemplateCreateModal(self.cog, self.guild_id, self.owner_id)
        await interaction.response.send_modal(modal)

# ===== MAIN COG =====
class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_cache: ConfigCache[GuildConfig] = ConfigCache(ttl=20.0, name="greeting_config")

    async def cog_load(self):
        # Tables are pre-configured in Supabase via SQL migrations
        pass

    async def get_config(self, guild_id: int) -> GuildConfig | None:
        async def _load():
            row = await self.bot.db_manager.fetch_safe(
                "greeting_config", {"guild_id": str(guild_id)}, single=True
            )
            if not row:
                return None
            return GuildConfig(
                guild_id=guild_id,
                welcome_channel=row.get("welcome_channel"),
                goodbye_channel=row.get("goodbye_channel"),
                boost_channel=row.get("boost_channel"),
                welcome_template_id=row.get("welcome_template_id"),
                goodbye_template_id=row.get("goodbye_template_id"),
                boost_template_id=row.get("boost_template_id"),
                welcome_enabled=bool(row.get("welcome_enabled", 1)),
                goodbye_enabled=bool(row.get("goodbye_enabled", 1)),
                boost_enabled=bool(row.get("boost_enabled", 1)),
                dm_on_welcome=bool(row.get("dm_on_welcome", 0)),
                log_channel=row.get("log_channel"),
            )

        return await self.config_cache.get(guild_id, _load)

    def invalidate_cache(self, guild_id: int):
        self.config_cache.invalidate(guild_id)

    def resolve_placeholders(self, text: str, member: discord.Member) -> str:
        if not text:
            return text
        now = discord.utils.utcnow()
        guild = member.guild
        replacements = {
            "{user:mention}": member.mention,
            "{user:name}": member.name,
            "{user:display_name}": member.display_name,
            "{user:id}": str(member.id),
            "{user:avatar}": str(member.display_avatar.url),
            "{user:created_at}": member.created_at.strftime("%Y-%m-%d %H:%M"),
            "{user:joined_at}": member.joined_at.strftime("%Y-%m-%d %H:%M") if member.joined_at else "N/A",
            "{server:name}": guild.name,
            "{server:id}": str(guild.id),
            "{server:members}": str(guild.member_count),
            "{server:icon}": str(guild.icon.url) if guild.icon else "",
            "{server:owner}": str(guild.owner),
            "{server:boost_count}": str(guild.premium_subscription_count or 0),
            "{server:boost_level}": str(guild.premium_tier),
            "{date}": now.strftime("%Y-%m-%d"),
            "{time}": now.strftime("%H:%M:%S"),
            "{newline}": "\n",
            "{random:greeting}": random.choice(RANDOM_GREETINGS) if RANDOM_GREETINGS else "",
        }
        replacements["{user}"] = member.mention
        replacements["{server}"] = guild.name
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def build_embed(self, template: dict, member: discord.Member) -> discord.Embed:
        embed = discord.Embed(
            title=self.resolve_placeholders(template.get("title", ""), member) or None,
            description=self.resolve_placeholders(template.get("description", ""), member),
            color=template.get("color", 0x090B1A),
            timestamp=discord.utils.utcnow()
        )
        if template.get("author_name"):
            embed.set_author(
                name=self.resolve_placeholders(template["author_name"], member),
                icon_url=self.resolve_placeholders(template.get("author_icon", ""), member) or None
            )
        thumb = self.resolve_placeholders(template.get("thumbnail", ""), member)
        if thumb:
            embed.set_thumbnail(url=thumb)
        img = self.resolve_placeholders(template.get("image", ""), member)
        if img:
            embed.set_image(url=img)
        if template.get("footer_text"):
            embed.set_footer(
                text=self.resolve_placeholders(template["footer_text"], member),
                icon_url=self.resolve_placeholders(template.get("footer_icon", ""), member) or None
            )
        else:
            embed.set_footer(text="𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 • Anime Chronicle")
        return embed

    def build_buttons(self, template: dict) -> View | None:
        buttons = template.get("buttons", [])
        if not isinstance(buttons, list) or not buttons:
            return None
        view = View(timeout=None)
        for btn_data in buttons[:25]:
            if not isinstance(btn_data, dict):
                logger.warning("Skipping malformed greeting button")
                continue
            url = btn_data.get("url", "")
            label = btn_data.get("label", "Товч")
            if not valid_button_url(url) or not isinstance(label, str) or not label:
                logger.warning("Skipping greeting button with an invalid link")
                continue
            btn = Button(
                label=label[:80],
                url=url,
                style=discord.ButtonStyle.link,
            )
            view.add_item(btn)
        return view if view.children else None

    async def save_template(
        self, guild_id: int, creator_id: int, template: dict,
        *, template_id: int | None = None,
    ) -> bool:
        data = {"name": template["name"], "data": json.dumps(template)}
        owner = {"guild_id": str(guild_id), "creator_id": str(creator_id)}
        if template_id is None:
            rows = await self.bot.db_manager.insert("greeting_templates", {**owner, **data})
        else:
            # Scope the write itself, including if the template changes after lookup.
            rows = await self.bot.db_manager.update(
                "greeting_templates", {"id": template_id, **owner}, data,
            )
        return bool(rows)

    async def get_template(
        self, template_id: int, guild_id: int, creator_id: int | None = None,
    ) -> dict | None:
        filters = {"id": template_id, "guild_id": str(guild_id)}
        if creator_id is not None:
            filters["creator_id"] = str(creator_id)
        row = await self.bot.db_manager.fetch_one("greeting_templates", filters)
        if not row:
            return None
        return self._decode_template(row, guild_id)

    @staticmethod
    def _decode_template(row: dict, guild_id: int) -> dict | None:
        try:
            template = json.loads(row["data"])
        except (KeyError, TypeError, ValueError):
            logger.warning("Malformed greeting template %s in guild %s", row.get("id"), guild_id, exc_info=True)
            return None
        return template if isinstance(template, dict) else None

    async def get_all_templates(self, guild_id: int, user_id: int | None = None) -> list[dict]:
        filters = {"guild_id": str(guild_id)}
        if user_id is not None:
            filters["creator_id"] = str(user_id)
        rows = await self.bot.db_manager.fetch_all("greeting_templates", filters)
        templates = []
        for row in rows:
            data = self._decode_template(row, guild_id)
            if data is not None:
                templates.append({
                    "id": row["id"], "name": row["name"], "data": data,
                    "creator_id": row["creator_id"],
                })
        return templates

    async def send_greeting(self, channel_id: int, template_id: int | None, member: discord.Member,
                            default_template: dict, send_dm: bool = False, log_channel_id: int | None = None):
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return
        template = await self.get_template(template_id, member.guild.id) if template_id else None
        # Deleted templates and stale/cross-guild configuration use the default.
        template = template or default_template
        embed = self.build_embed(template, member)
        view = self.build_buttons(template)
        try:
            await channel.send(embed=embed, view=view)
        except discord.HTTPException as e:
            await self.log_error(member.guild, f"Мэндчилгээ илгээхэд алдаа гарлаа: {e}", log_channel_id)

        if send_dm:
            try:
                await member.send(embed=embed, view=view)
            except discord.HTTPException:
                logger.debug("Cannot send greeting DM to member %s in guild %s", member.id, member.guild.id, exc_info=True)

    async def log_error(self, guild: discord.Guild, message: str, log_channel_id: int | None = None):
        logger.warning("Greeting error in guild %s: %s", guild.id, message)
        if not log_channel_id:
            return
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            try:
                await log_channel.send(embed=discord.Embed(description=message, color=ERROR_COLOR))
            except discord.HTTPException:
                logger.warning("Cannot send greeting error log in guild %s", guild.id, exc_info=True)

    # ================= SLASH COMMANDS =================
    @app_commands.command(name="greeting_set", description="Welcome/Goodbye/Boost сувгийг тохируулах")
    @app_commands.describe(
        event="Үйл явдал",
        channel="Мэдэгдэл очих суваг",
        template_id="Загварын ID (заавал биш)",
        dm="Welcome үед DM илгээх эсэх (зөвхөн welcome)"
    )
    @app_commands.choices(event=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
        app_commands.Choice(name="Boost", value="boost")
    ])
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greeting_set(self, interaction: discord.Interaction, event: str, channel: discord.TextChannel,
                           template_id: int | None = None, dm: bool | None = None):
        if event not in {"welcome", "goodbye", "boost"}:
            return await interaction.response.send_message("❌ Үйл явдал буруу байна.", ephemeral=True)
        if channel.guild.id != interaction.guild_id:
            return await interaction.response.send_message("❌ Энэ серверийн суваг сонгоно уу.", ephemeral=True)
        if template_id is not None and not await self.get_template(
            template_id, interaction.guild_id, interaction.user.id,
        ):
            return await interaction.response.send_message("❌ Таны загвар энэ серверт олдсонгүй.", ephemeral=True)
        col_channel = f"{event}_channel"
        col_template = f"{event}_template_id"
        data = {col_channel: channel.id, col_template: template_id}
        if dm is not None and event == "welcome":
            data["dm_on_welcome"] = int(dm)
        await self.bot.db_manager.upsert(
            "greeting_config",
            {"guild_id": str(interaction.guild.id), **data},
            on_conflict="guild_id",
        )
        self.invalidate_cache(interaction.guild.id)
        embed = discord.Embed(
            title="✅ Амжилттай тохируулагдлаа",
            description=f"**Үйл явдал:** {event.capitalize()}\n**Суваг:** {channel.mention}\n**Загвар ID:** {template_id or 'Анхдагч'}"
                        + (f"\n**DM мэндчилгээ:** {'Идэвхтэй' if dm else 'Идэвхгүй'}" if dm is not None else ""),
            color=SUCCESS_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_toggle", description="Мэдэгдлийг идэвхжүүлэх/унтраах")
    @app_commands.describe(event="Үйл явдал")
    @app_commands.choices(event=[
        app_commands.Choice(name="Welcome", value="welcome"),
        app_commands.Choice(name="Goodbye", value="goodbye"),
        app_commands.Choice(name="Boost", value="boost"),
        app_commands.Choice(name="DM Welcome", value="dm")
    ])
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greeting_toggle(self, interaction: discord.Interaction, event: str):
        if event not in {"welcome", "goodbye", "boost", "dm"}:
            return await interaction.response.send_message("❌ Үйл явдал буруу байна.", ephemeral=True)
        config = await self.get_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ Тохиргоо байхгүй. `/greeting_set` ашиглана уу.", ephemeral=True)

        if event == "dm":
            new_state = not config.dm_on_welcome
            await self.bot.db_manager.update(
                "greeting_config",
                {"guild_id": str(interaction.guild.id)},
                {"dm_on_welcome": int(new_state)},
            )
            self.invalidate_cache(interaction.guild.id)
            desc = "DM welcome **{}**".format("✅ Идэвхжлээ" if new_state else "❌ Унтарлаа")
        else:
            col = f"{event}_enabled"
            current = getattr(config, col)
            new_state = not current
            await self.bot.db_manager.update(
                "greeting_config",
                {"guild_id": str(interaction.guild.id)},
                {col: int(new_state)},
            )
            self.invalidate_cache(interaction.guild.id)
            desc = f"{event.capitalize()} мэдэгдэл **{'✅ Идэвхжлээ' if new_state else '❌ Унтарлаа'}**"

        embed = discord.Embed(title="🔄 Төлөв өөрчлөгдлөө", description=desc, color=SUCCESS_COLOR if new_state else WARNING_COLOR)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="template_create", description="Шинэ embed загвар үүсгэх")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def template_create(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📝 Шинэ Embed Загвар бүтээх",
            description="Доорх товчийг дарж загвар үүсгэх modal-ийг нээнэ үү.\n\n"
                        "**Бэлэн хувьсагчдын жагсаалтыг `/placeholders` командаар харна уу.**",
            color=GOLD_COLOR
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        view = TemplateCreateView(self, interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="template_edit", description="Загварыг засварлах")
    @app_commands.describe(template_id="Загварын ID")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def template_edit(self, interaction: discord.Interaction, template_id: int):
        template = await self.get_template(template_id, interaction.guild_id, interaction.user.id)
        if not template:
            return await interaction.response.send_message("❌ Загвар олдсонгүй.", ephemeral=True)
        modal = TemplateCreateModal(
            self, interaction.guild_id, interaction.user.id,
            existing=template, template_id=template_id,
        )
        await interaction.response.send_modal(modal)

    @app_commands.command(name="template_delete", description="Загвар устгах")
    @app_commands.describe(template_id="Загварын ID")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def template_delete(self, interaction: discord.Interaction, template_id: int):
        await interaction.response.defer(ephemeral=True)
        deleted = await self.bot.db_manager.delete("greeting_templates", {
            "id": template_id, "guild_id": str(interaction.guild_id),
            "creator_id": str(interaction.user.id),
        })
        if not deleted:
            return await interaction.followup.send("❌ Таны загвар энэ серверт олдсонгүй.", ephemeral=True)
        for event in ("welcome", "goodbye", "boost"):
            column = f"{event}_template_id"
            await self.bot.db_manager.update(
                "greeting_config", {"guild_id": str(interaction.guild_id), column: template_id},
                {column: None},
            )
        self.invalidate_cache(interaction.guild_id)
        await interaction.followup.send(f"✅ Загвар {template_id} устгагдлаа.", ephemeral=True)

    @app_commands.command(name="template_list", description="Бүх загваруудыг харах")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def template_list(self, interaction: discord.Interaction):
        templates = await self.get_all_templates(interaction.guild.id, interaction.user.id)
        if not templates:
            return await interaction.response.send_message("❌ Танд ямар ч загвар байхгүй байна.", ephemeral=True)
        embed = discord.Embed(title="📋 Таны загварууд", color=INFO_COLOR)
        for t in templates[:15]:
            embed.add_field(
                name=f"ID: {t['id']} — {t['name']}",
                value=f"```{t['data'].get('description', '')[:80]}...```",
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="template_preview", description="Загварыг урьдчилан харах")
    @app_commands.describe(template_id="Загварын ID", member="Гишүүний нэр дээр харуулах")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def template_preview(self, interaction: discord.Interaction, template_id: int, member: discord.Member | None = None):
        template = await self.get_template(template_id, interaction.guild_id, interaction.user.id)
        if not template:
            return await interaction.response.send_message("❌ Загвар олдсонгүй.", ephemeral=True)
        target = member or interaction.user
        if not isinstance(target, discord.Member) or target.guild.id != interaction.guild_id:
            return await interaction.response.send_message("❌ Энэ серверийн гишүүн сонгоно уу.", ephemeral=True)
        embed = self.build_embed(template, target)
        view = self.build_buttons(template)
        await interaction.response.send_message(
            f"👁️ Загвар ID {template_id}-н урьдчилсан харагдац:",
            embed=embed,
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="placeholders", description="Бүх хувьсагчдыг харах")
    async def placeholders(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Хувьсагчдын жагсаалт",
            description="Welcome/Goodbye/Boost загвартаа дараах хувьсагчдыг ашиглана уу.",
            color=GOLD_COLOR
        )
        for placeholder, desc in PLACEHOLDERS.items():
            embed.add_field(name=placeholder, value=desc, inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_status", description="Одоогийн тохиргоог харах")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def greeting_status(self, interaction: discord.Interaction):
        config = await self.get_config(interaction.guild.id)
        if not config:
            return await interaction.response.send_message("❌ Одоогоор тохиргоо хийгдээгүй.", ephemeral=True)
        embed = discord.Embed(title="📊 Одоогийн тохиргоо", color=INFO_COLOR)
        embed.add_field(name="Welcome", value=f"Суваг: {'<#'+str(config.welcome_channel)+'>' if config.welcome_channel else 'Тохируулаагүй'}\n"
                                               f"Идэвхтэй: {'✅' if config.welcome_enabled else '❌'}\n"
                                               f"Загвар ID: {config.welcome_template_id or 'Анхдагч'}\n"
                                               f"DM: {'✅' if config.dm_on_welcome else '❌'}", inline=False)
        embed.add_field(name="Goodbye", value=f"Суваг: {'<#'+str(config.goodbye_channel)+'>' if config.goodbye_channel else 'Тохируулаагүй'}\n"
                                               f"Идэвхтэй: {'✅' if config.goodbye_enabled else '❌'}\n"
                                               f"Загвар ID: {config.goodbye_template_id or 'Анхдагч'}", inline=False)
        embed.add_field(name="Boost", value=f"Суваг: {'<#'+str(config.boost_channel)+'>' if config.boost_channel else 'Тохируулаагүй'}\n"
                                             f"Идэвхтэй: {'✅' if config.boost_enabled else '❌'}\n"
                                             f"Загвар ID: {config.boost_template_id or 'Анхдагч'}", inline=False)
        if config.log_channel:
            embed.add_field(name="Лог суваг", value=f"<#{config.log_channel}>", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="greeting_reset", description="Бүх тохиргоог устгах (болгоомжтой!)")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def greeting_reset(self, interaction: discord.Interaction):
        await self.bot.db_manager.delete("greeting_config", {"guild_id": str(interaction.guild.id)})
        self.invalidate_cache(interaction.guild.id)
        await interaction.response.send_message("🧹 Бүх мэндчилгээний тохиргоо устгагдлаа.", ephemeral=True)

    @app_commands.command(name="set_log_channel", description="Алдааны лог сувгийг тохируулах")
    @app_commands.describe(channel="Лог суваг")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        if channel.guild.id != interaction.guild_id:
            return await interaction.response.send_message("❌ Энэ серверийн суваг сонгоно уу.", ephemeral=True)
        await self.bot.db_manager.upsert(
            "greeting_config",
            {"guild_id": str(interaction.guild.id), "log_channel": channel.id},
            on_conflict="guild_id",
        )
        self.invalidate_cache(interaction.guild.id)
        await interaction.response.send_message(f"✅ Лог суваг: {channel.mention}", ephemeral=True)

    # ================= EVENT LISTENERS =================
    @commands.Cog.listener()
    async def on_member_join(self, member):
        try:
            config = await self.get_config(member.guild.id)
            if config and config.is_welcome_active:
                await self.send_greeting(
                    config.welcome_channel, config.welcome_template_id, member,
                    DEFAULT_TEMPLATES["welcome"],
                    send_dm=config.dm_on_welcome,
                    log_channel_id=config.log_channel
                )
        except Exception:
            logger.exception("Greetings on_member_join failed in guild %s", member.guild.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        try:
            config = await self.get_config(member.guild.id)
            if config and config.is_goodbye_active:
                await self.send_greeting(
                    config.goodbye_channel, config.goodbye_template_id, member,
                    DEFAULT_TEMPLATES["goodbye"],
                    log_channel_id=config.log_channel
                )
        except Exception:
            logger.exception("Greetings on_member_remove failed in guild %s", member.guild.id)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.premium_since is None and after.premium_since is not None:
            try:
                config = await self.get_config(after.guild.id)
                if config and config.is_boost_active:
                    await self.send_greeting(
                        config.boost_channel, config.boost_template_id, after,
                        DEFAULT_TEMPLATES["boost"],
                        log_channel_id=config.log_channel
                    )
            except Exception:
                logger.exception("Greetings on_member_update failed in guild %s", after.guild.id)

async def setup(bot):
    await bot.add_cog(Greetings(bot))
