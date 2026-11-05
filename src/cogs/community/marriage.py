import asyncio
import datetime
import io
import logging
import math
import time
from typing import ClassVar

import aiohttp
import discord
from discord import ButtonStyle, app_commands, ui
from discord.ext import commands
from discord.ui import Button, View
from PIL import Image, ImageDraw

from src.ui.setup import (
    SetupPanel,
    SetupState,
    disable_setup_panel,
    mention_or_missing,
    state_text,
    sync_toggle_button,
)
from src.utils import journal_style as journal
from src.utils.fonts import draw_text_with_fallback

# ---------- Centralized Unicode-aware font management ----------
from src.utils.fonts import load_font as _load_font
from src.utils.supabase_cog import SupabaseCog

logger = logging.getLogger(__name__)

# Avatar/card зургийн хэмжээний дээд хязгаар (5 MiB).
MAX_AVATAR_BYTES = 5 * 1024 * 1024

# ══════════════ ӨНГӨНҮҮД ══════════════
EMBED_COLOR = 0x1e1e2f
SUCCESS_COLOR = 0xa6e3a1
ERROR_COLOR = 0xf38ba8
WARNING_COLOR = 0xf9e2af
GOLD_COLOR = 0xfab387
PURPLE_COLOR = 0xcba6f7
LOVE_COLOR = 0xff69b4
INFO_COLOR = 0x89b4fa

PROPOSAL_TIMEOUT = 120

GIFTS = {
    "flower":    {"name": "🌹 Цэцэг",        "emoji": "🌹", "love": 5, "item_id": 11},
    "chocolate": {"name": "🍫 Шоколад",     "emoji": "🍫", "love": 10, "item_id": 60},
    "ring":      {"name": "💍 Бөгж",        "emoji": "💍", "love": 50, "item_id": 12},
    "necklace":  {"name": "📿 Зүүлт",       "emoji": "📿", "love": 30, "item_id": 80},
    "teddy":     {"name": "🧸 Тедди",       "emoji": "🧸", "love": 15, "item_id": 70},
}

FAMILY_RELATIONS = {
    "grandfather": ("👴 Өвөө", "grandchild", "🧒 Ач/зээ"),
    "grandmother": ("👵 Эмээ", "grandchild", "🧒 Ач/зээ"),
    "father": ("👨 Аав", "child", "🧒 Хүүхэд"),
    "mother": ("👩 Ээж", "child", "🧒 Хүүхэд"),
    "older_brother": ("👦 Ах", "younger_sibling", "🧒 Дүү"),
    "older_sister": ("👧 Эгч", "younger_sibling", "🧒 Дүү"),
    "younger_brother": ("👦 Эрэгтэй дүү", "older_sibling", "🧑 Ах/эгч"),
    "younger_sister": ("👧 Эмэгтэй дүү", "older_sibling", "🧑 Ах/эгч"),
    "child": ("🧒 Хүүхэд", "parent", "👪 Эцэг эх"),
}


def family_relation_label(value: str) -> str:
    if value in FAMILY_RELATIONS:
        return FAMILY_RELATIONS[value][0]
    for _, reverse, reverse_label in FAMILY_RELATIONS.values():
        if value == reverse:
            return reverse_label
    return "👥 Гэр бүлийн холбоо"

# ══════════════ VIEWS ══════════════
class ProposalView(View):
    def __init__(self, cog, guild_id, proposer_id, target_id, ring_name, ring_emoji, ring_item_id):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id
        self.proposer_id = proposer_id
        self.target_id = target_id
        self.ring_name = ring_name
        self.ring_emoji = ring_emoji
        self.ring_item_id = ring_item_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("❌ Энэ санал өөр серверийнх байна.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        guild = interaction.guild
        proposer = guild.get_member(self.proposer_id)
        if not proposer:
            return await interaction.response.send_message("❌ Санал тавьсан хүн серверээс гарсан.", ephemeral=True)

        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        shop = self.cog.bot.get_cog("ShopCog")
        # The ring is the cost of the marriage, so consume it BEFORE the
        # marriage is written. Removing it afterwards meant a failed removal
        # reported an error while the marriage row already existed.
        if shop and self.ring_item_id and not await shop.remove_item(
            self.proposer_id, self.guild_id, self.ring_item_id, 1
        ):
            return await interaction.followup.send(
                "❌ Бүтээгэрийн бүлгэм цагийн өнгө байхгүй болсон. Дахин оролдоно уу.",
                ephemeral=True,
            )

        await self.cog.add_marriage(self.guild_id, self.proposer_id, self.target_id, self.ring_name, self.ring_emoji)

        await self.cog.announce_marriage(guild, proposer, interaction.user)
        await self.cog.grant_marriage_role(guild, proposer)
        await self.cog.grant_marriage_role(guild, interaction.user)

        embed = discord.Embed(
            title="💒 ГЭРЛЭЛТ БҮРТГЭГДЛЭЭ!",
            description=f"{proposer.mention} болон {interaction.user.mention} гэрлэлээ!\n💍 Бөгж: {self.ring_emoji} {self.ring_name}",
            color=LOVE_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.target_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        proposer = interaction.guild.get_member(self.proposer_id)
        embed = discord.Embed(
            title="💔 ТАТГАЛЗСАН",
            description=f"{interaction.user.mention} {proposer.mention if proposer else 'хэрэглэгч'}-ийн саналаас татгалзлаа.",
            color=ERROR_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except discord.HTTPException:
                logger.warning("Could not disable marriage proposal in guild %s", self.guild_id, exc_info=True)


class FamilyRelationRequestView(View):
    def __init__(self, cog, guild_id, requester_id, target_id, relation_type):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.cog = cog
        self.guild_id = guild_id
        self.requester_id = requester_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.target_id:
            await interaction.response.send_message("❌ Энэ хүсэлт танд зориулагдаагүй.", ephemeral=True)
            return False
        return True

    async def finish(self, interaction, accepted):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.cog.bot.db_manager.delete(
            "marriage_proposals",
            {
                "guild_id": str(self.guild_id),
                "from_id": str(self.requester_id),
                "to_id": str(self.target_id),
                "proposal_type": f"family_{self.relation_type}",
            },
        )
        if accepted:
            await self.cog.add_family_relation(
                self.guild_id, self.requester_id, self.target_id, self.relation_type
            )
        requester = interaction.guild.get_member(self.requester_id)
        relation = family_relation_label(self.relation_type)
        title = "✅ ГЭР БҮЛИЙН ХОЛБОО ҮҮСЛЭЭ" if accepted else "❌ ХҮСЭЛТЭЭС ТАТГАЛЗЛАА"
        description = (
            f"{requester.mention if requester else f'<@{self.requester_id}>'} → "
            f"{interaction.user.mention}\n{relation}"
        )
        await interaction.followup.send(
            embed=discord.Embed(title=title, description=description, color=SUCCESS_COLOR if accepted else WARNING_COLOR)
        )
        self.stop()

    @ui.button(label="Зөвшөөрөх", emoji="✅", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        await self.finish(interaction, True)

    @ui.button(label="Татгалзах", emoji="❌", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        await self.finish(interaction, False)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                logger.warning("Could not disable family relation request", exc_info=True)

class AdoptView(View):
    def __init__(self, bot, guild_id, parent_id, child_id, proposal_type="adoption", relationship_type="family"):
        super().__init__(timeout=PROPOSAL_TIMEOUT)
        self.bot = bot
        self.guild_id = guild_id
        self.parent_id = parent_id
        self.child_id = child_id
        self.proposal_type = proposal_type
        self.relationship_type = relationship_type
        self.recipient_id = parent_id if proposal_type == "parenthood" else child_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("❌ Энэ санал өөр серверийнх байна.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Зөвшөөрөх", style=ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.recipient_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.bot.db_manager.delete(
            "marriage_proposals",
            {"guild_id": str(self.guild_id), "from_id": str(self.child_id if self.proposal_type == "parenthood" else self.parent_id), "to_id": str(self.recipient_id), "proposal_type": self.proposal_type},
        )
        await self.bot.db_manager.insert("adoptions", {
            "guild_id": str(self.guild_id),
            "parent_id": str(self.parent_id),
            "child_id": str(self.child_id),
            "type": self.relationship_type,
            "adopted_since": int(time.time()),
        })
        parent = interaction.guild.get_member(self.parent_id)
        child_member = interaction.guild.get_member(self.child_id)
        parent_mention = parent.mention if parent else f"<@{self.parent_id}>"
        child_mention = child_member.mention if child_member else f"<@{self.child_id}>"
        embed = discord.Embed(
            title="👨‍👧‍👦 ӨРГӨМЖЛӨЛТ БАТЛАГДЛАА" if self.proposal_type=="adoption" else "👪 ЭЦЭГ ЭХ БОЛЛОО",
            description=f"{parent_mention} болон {child_mention} эцэг эх, хүүхдийн харилцаагаа баталгаажууллаа!",
            color=SUCCESS_COLOR
        )
        await interaction.followup.send(embed=embed)
        self.stop()

    @discord.ui.button(label="❌ Татгалзах", style=ButtonStyle.secondary)
    async def decline_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.recipient_id:
            return await interaction.response.send_message("❌ Энэ товч танд зориулагдаагүй!", ephemeral=True)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        await self.bot.db_manager.delete(
            "marriage_proposals",
            {"guild_id": str(self.guild_id), "from_id": str(self.child_id if self.proposal_type == "parenthood" else self.parent_id), "to_id": str(self.recipient_id), "proposal_type": self.proposal_type},
        )
        embed = discord.Embed(title="👶 ТАТГАЛЗСАН", description=f"{interaction.user.mention} саналаас татгалзлаа.", color=WARNING_COLOR)
        await interaction.followup.send(embed=embed)
        self.stop()

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try: await self.message.edit(view=self)
            except discord.HTTPException:
                logger.warning("Could not disable adoption proposal in guild %s", self.guild_id, exc_info=True)


class MarriageHubView(View):
    """Private, owner-bound dashboard for the most common marriage actions."""

    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ marriage цэс таных биш.", ephemeral=True)
            return False
        return True

    @staticmethod
    def build_embed(section="home"):
        pages = {
            "home": (
                "💍 AETHER BONDS",
                "Доорх сонголтоор заавар харж, товчоор өөрийн мэдээлэл рүү шууд орно.",
                "🌸 Anime relationship hub • 5 минут идэвхтэй",
            ),
            "couple": (
                "💞 Хосын үйлдэл",
                ("`/marriage propose @user` — санал тавих\n"
                 "`/marriage divorce [user]` — салалт\n"
                 "`/marriage love @user` — өдөр тутмын love\n"
                 "`/marriage gift <gift>` — бэлэг өгөх"),
                "Санал хүлээн авагч Accept эсвэл Decline дарна.",
            ),
            "family": (
                "👨‍👩‍👧‍👦 Гэр бүл",
                ("`/marriage adopt @user` — хүүхэд үрчлэх\n"
                 "`/marriage request-parent @user` — эцэг эх хүсэх\n"
                 "`/marriage disown @user` — хүүхдийн холбоо цуцлах\n"
                 "`/marriage leave-family` — эцэг эхийн холбоо цуцлах"),
                "Family болон Tree товчоор өөрийн мэдээллийг шууд харна.",
            ),
            "settings": (
                "🔐 Нууцлал ба тохиргоо",
                ("Privacy товч — гэрлэх санал авах эрхийг шууд асааж/унтраана.\n"
                 "`/marriage setup` — админы серверийн тохиргоо."),
                "Таны сонголт зөвхөн энэ серверт хадгалагдана.",
            ),
        }
        title, description, footer = pages.get(section, pages["home"])
        embed = discord.Embed(title=title, description=description, color=LOVE_COLOR)
        embed.set_footer(text=footer)
        return embed

    @ui.select(
        placeholder="✨ Зааврын ангилал сонгох",
        options=[
            discord.SelectOption(label="Нүүр", value="home", emoji="🌸"),
            discord.SelectOption(label="Хос", value="couple", emoji="💞"),
            discord.SelectOption(label="Гэр бүл", value="family", emoji="👨‍👩‍👧‍👦"),
            discord.SelectOption(label="Нууцлал", value="settings", emoji="🔐"),
        ],
        row=0,
    )
    async def section_select(self, interaction: discord.Interaction, select: ui.Select):
        await interaction.response.edit_message(embed=self.build_embed(select.values[0]), view=self)

    @ui.button(label="Санал тавих", emoji="💍", style=ButtonStyle.success, row=1)
    async def propose_button(self, interaction: discord.Interaction, button: Button):
        view = MarriageTargetView(self.cog, self.guild_id, self.author_id, "propose")
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @ui.button(label="Гэр бүл", emoji="👨‍👩‍👧‍👦", style=ButtonStyle.primary, row=1)
    async def family_button(self, interaction: discord.Interaction, button: Button):
        view = MarriageFamilyView(self.cog, self.guild_id, self.author_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @ui.button(label="Миний profile", emoji="💖", style=ButtonStyle.secondary, row=1)
    async def profile_button(self, interaction: discord.Interaction, button: Button):
        await self.cog._marriage_card(interaction, None, is_slash=True)

    @ui.button(label="Миний tree", emoji="🌳", style=ButtonStyle.secondary, row=1)
    async def tree_button(self, interaction: discord.Interaction, button: Button):
        await self.cog._family_tree(interaction, None, is_slash=True)

    @ui.button(label="Privacy солих", emoji="🔐", style=ButtonStyle.success, row=2)
    async def privacy_button(self, interaction: discord.Interaction, button: Button):
        blocked = await self.cog.is_blocked(self.guild_id, self.author_id)
        await self.cog.set_blocked(self.guild_id, self.author_id, not blocked)
        state = "ХААЛТТАЙ" if not blocked else "НЭЭЛТТЭЙ"
        await interaction.response.send_message(f"🔐 Гэрлэх санал: **{state}**", ephemeral=True)


class MarriageTargetView(View):
    ACTIONS: ClassVar[dict[str, tuple[str, str]]] = {
        "propose": ("💍 Гэрлэх санал", "Гэрлэх санал тавих хүнээ сонгоно уу."),
        "adopt_son": ("👦 Хүү үрчлэх", "Хүүгээр үрчлэх хүнээ сонгоно уу."),
        "adopt_daughter": ("👧 Охин үрчлэх", "Охиноор үрчлэх хүнээ сонгоно уу."),
        "request_father": ("👨 Аав хүсэх", "Ааваар сонгох хүнээ сонгоно уу."),
        "request_mother": ("👩 Ээж хүсэх", "Ээжээр сонгох хүнээ сонгоно уу."),
    }

    def __init__(self, cog, guild_id, author_id, action):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.action = action

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ marriage цэс таных биш.", ephemeral=True)
            return False
        return True

    def build_embed(self):
        if self.action.startswith("family:"):
            relation = self.action.split(":", 1)[1]
            title = family_relation_label(relation)
            description = "Энэ холбооны хүсэлт явуулах хүнээ сонгоно уу."
        elif self.action == "remove_family":
            title, description = "✂️ Холбоо салгах", "Салгах гэр бүлийн хүнээ сонгоно уу."
        else:
            title, description = self.ACTIONS[self.action]
        return discord.Embed(title=title, description=description, color=LOVE_COLOR)

    @ui.select(cls=ui.UserSelect, placeholder="👤 Хэрэглэгч сонгох", min_values=1, max_values=1, row=0)
    async def target_select(self, interaction: discord.Interaction, select: ui.UserSelect):
        target = select.values[0]
        if self.action == "propose":
            await self.cog._propose(interaction, target, is_slash=True)
        elif self.action.startswith("family:"):
            await self.cog._request_family_relation(
                interaction, target, self.action.split(":", 1)[1], is_slash=True
            )
        elif self.action == "remove_family":
            await self.cog._remove_family_relation(interaction, target, is_slash=True)
        elif self.action == "adopt_son":
            await self.cog._adopt(interaction, target, child_role="son", is_slash=True)
        elif self.action == "adopt_daughter":
            await self.cog._adopt(interaction, target, child_role="daughter", is_slash=True)
        elif self.action == "request_father":
            await self.cog._makeparent(interaction, target, parent_role="father", is_slash=True)
        else:
            await self.cog._makeparent(interaction, target, parent_role="mother", is_slash=True)

    @ui.button(label="Буцах", emoji="↩️", style=ButtonStyle.secondary, row=1)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        view = MarriageHubView(self.cog, self.guild_id, self.author_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class MarriageFamilyView(View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ marriage цэс таных биш.", ephemeral=True)
            return False
        return True

    @staticmethod
    def build_embed():
        return discord.Embed(
            title="👨‍👩‍👧‍👦 Гэр бүлийн үйлдэл",
            description="Харах мэдээлэл эсвэл үүсгэх гэр бүлийн холбоогоо сонгоно уу.",
            color=PURPLE_COLOR,
        )

    async def open_picker(self, interaction, action):
        view = MarriageTargetView(self.cog, self.guild_id, self.author_id, action)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @ui.button(label="Миний гэр бүл", emoji="🏠", style=ButtonStyle.primary, row=0)
    async def overview_button(self, interaction, button):
        await self.cog._family_overview(interaction, None, is_slash=True)

    @ui.button(label="Холбоо нэмэх", emoji="➕", style=ButtonStyle.success, row=0)
    async def add_button(self, interaction, button):
        view = MarriageRelationTypeView(self.cog, self.guild_id, self.author_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @ui.button(label="Холбоо салгах", emoji="✂️", style=ButtonStyle.danger, row=1)
    async def remove_button(self, interaction, button):
        await self.open_picker(interaction, "remove_family")

    @ui.button(label="Буцах", emoji="↩️", style=ButtonStyle.secondary, row=2)
    async def back_button(self, interaction, button):
        view = MarriageHubView(self.cog, self.guild_id, self.author_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


class MarriageRelationTypeView(View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ marriage цэс таных биш.", ephemeral=True)
            return False
        return True

    @staticmethod
    def build_embed():
        return discord.Embed(
            title="➕ Гэр бүлийн холбоо нэмэх",
            description="Хүсэлтээр үүсгэх холбооны төрлөө сонгоно уу.",
            color=PURPLE_COLOR,
        )

    @ui.select(
        placeholder="Холбооны төрөл сонгох",
        options=[discord.SelectOption(label=label.split(" ", 1)[1], value=value, emoji=label.split(" ", 1)[0])
                 for value, (label, _, _) in FAMILY_RELATIONS.items()],
        row=0,
    )
    async def relation_select(self, interaction: discord.Interaction, select: ui.Select):
        view = MarriageTargetView(
            self.cog, self.guild_id, self.author_id, f"family:{select.values[0]}"
        )
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

    @ui.button(label="Буцах", emoji="↩️", style=ButtonStyle.secondary, row=1)
    async def back_button(self, interaction, button):
        view = MarriageFamilyView(self.cog, self.guild_id, self.author_id)
        await interaction.response.edit_message(embed=view.build_embed(), view=view)

# ══════════════ АДМИН САМБАР ══════════════
class MarriageSetupView(View):
    def __init__(self, cog, guild_id, author_id):
        super().__init__(timeout=600)
        self.cog = cog
        self.guild_id = guild_id
        self.author_id = author_id
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None or interaction.guild.id != self.guild_id:
            await interaction.response.send_message("❌ Энэ самбар өөр серверийнх байна.", ephemeral=True)
            return False
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Энэ самбар таных биш.", ephemeral=True)
            return False
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Administrator эрх шаардлагатай.", ephemeral=True)
            return False
        return True

    async def refresh(self, interaction: discord.Interaction):
        cfg = await self.cog.get_guild_config(self.guild_id)
        embed = self.build_embed(cfg, interaction.guild)
        if self.message is not None:
            await self.message.edit(embed=embed, view=self)
        else:
            logger.warning("Marriage setup panel has no bound message in guild %s", self.guild_id)

    def build_embed(self, cfg, guild):
        channel = guild.get_channel(cfg.get("announce_channel", 0))
        role = guild.get_role(cfg.get("marriage_role", 0))
        enabled = bool(cfg["enabled"])
        panel = SetupPanel(
            "Гэрлэлтийн систем",
            "Системийн дүрэм, мэдэгдэл болон автоматаар олгох ролийг удирдана.",
            icon="💍",
            state=SetupState.READY if enabled else SetupState.DISABLED,
            status="Гэрлэлтийн систем ажиллаж байна" if enabled else "Систем унтраалттай",
            color=PURPLE_COLOR,
        )
        panel.section("Үндсэн дүрэм", [
            f"🔘 Систем  {state_text(enabled)}",
            f"❤️ Полигами  {'✅ Зөвшөөрсөн' if cfg['polygamy'] else '⛔ Хориотой'}",
            f"👥 Нэг хэрэглэгчийн дээд хязгаар  **{cfg['max_spouses']}**",
        ], icon="⚙️")
        panel.section("Discord холболт", [
            f"📣 Мэдэгдэл  {mention_or_missing(channel)}",
            f"💑 Гэрлэлтийн роль  {mention_or_missing(role)}",
        ], icon="🔗")
        sync_toggle_button(
            self.toggle_enabled,
            enabled,
            disable_label="Систем унтраах",
            enable_label="Систем асаах",
        )
        self.toggle_polygamy.label = (
            "Полигами хориглох" if cfg["polygamy"] else "Полигами зөвшөөрөх"
        )
        return panel.finish("Самбар 10 минут идэвхтэй")

    @ui.select(cls=ui.ChannelSelect, channel_types=[discord.ChannelType.text], placeholder="📢 Мэдэгдэл суваг", row=0)
    async def select_channel(self, interaction, select: ui.ChannelSelect):
        await self.cog.set_guild_config(self.guild_id, announce_channel=select.values[0].id)
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="Систем асаах", emoji="▶️", style=discord.ButtonStyle.success, row=1)
    async def toggle_enabled(self, interaction, button):
        cfg = await self.cog.get_guild_config(self.guild_id)
        await self.cog.set_guild_config(self.guild_id, enabled=not cfg["enabled"])
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="Полигами зөвшөөрөх", emoji="❤️", style=discord.ButtonStyle.secondary, row=1)
    async def toggle_polygamy(self, interaction, button):
        cfg = await self.cog.get_guild_config(self.guild_id)
        await self.cog.set_guild_config(self.guild_id, polygamy=not cfg["polygamy"])
        await interaction.response.defer()
        await self.refresh(interaction)

    @ui.button(label="👥 Макс гэрлэлт", style=discord.ButtonStyle.secondary, row=2)
    async def max_spouses_button(self, interaction, button):
        await interaction.response.send_modal(MaxSpousesModal(self))

    @ui.button(label="💑 Роль", style=discord.ButtonStyle.secondary, row=2)
    async def role_button(self, interaction, button):
        await interaction.response.send_modal(MarriageRoleModal(self))

    @ui.button(label="🔄 Шинэчлэх", style=discord.ButtonStyle.gray, row=3)
    async def refresh_button(self, interaction, button):
        await interaction.response.defer()
        await self.refresh(interaction)

    async def on_timeout(self):
        await disable_setup_panel(self, self.message)

class MaxSpousesModal(ui.Modal, title="Хамгийн их гэрлэх тоо"):
    amount = ui.TextInput(label="Тоо", placeholder="1", required=True)
    def __init__(self, view): super().__init__(); self.view = view
    async def on_submit(self, interaction):
        if not await self.view.interaction_check(interaction):
            return
        try:
            val = int(self.amount.value)
            if val < 1: raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Буруу утга.", ephemeral=True)
        await self.view.cog.set_guild_config(self.view.guild_id, max_spouses=val)
        await interaction.response.send_message(f"✅ {val}", ephemeral=True)
        await self.view.refresh(interaction)

class MarriageRoleModal(ui.Modal, title="Гэрлэлтийн роль ID"):
    role_id = ui.TextInput(label="Роль ID", placeholder="123456789", required=True)
    def __init__(self, view): super().__init__(); self.view = view
    async def on_submit(self, interaction):
        if not await self.view.interaction_check(interaction):
            return
        try:
            rid = int(self.role_id.value)
        except ValueError:
            return await interaction.response.send_message("❌ Буруу ID.", ephemeral=True)
        role = interaction.guild.get_role(rid)
        if not role:
            return await interaction.response.send_message("❌ Роль олдсонгүй.", ephemeral=True)
        await self.view.cog.set_guild_config(self.view.guild_id, marriage_role=rid)
        await interaction.response.send_message(f"✅ {role.mention}", ephemeral=True)
        await self.view.refresh(interaction)

# ══════════════ ҮНДСЭН COG ══════════════
class Marriage(SupabaseCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            raise commands.NoPrivateMessage
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild is None:
            raise app_commands.NoPrivateMessage
        return True

    async def init_db(self):
        # Tables are pre-configured in Supabase
        pass

    async def cog_load(self):
        # Tables are pre-configured in Supabase
        pass

    # ═════════ ХЭРЭГЛЭГЧИЙН ФУНКЦУУД ═════════
    async def get_guild_config(self, guild_id):
        row = await self.bot.db_manager.fetch_one("marriage_guild_config", {"guild_id": str(guild_id)})
        if not row:
            return {"enabled": True, "polygamy": False, "max_spouses": 1, "announce_channel": None, "marriage_role": None}
        return {"enabled": bool(row.get("enabled", 1)), "polygamy": bool(row.get("polygamy", 0)),
                "max_spouses": row.get("max_spouses", 1), "announce_channel": row.get("announce_channel"),
                "marriage_role": row.get("marriage_role")}

    async def set_guild_config(self, guild_id, **kwargs):
        gid = str(guild_id)
        data = {"guild_id": gid}
        data.update(kwargs)
        await self.bot.db_manager.upsert("marriage_guild_config", data, on_conflict="guild_id")

    async def grant_marriage_role(self, guild, member):
        cfg = await self.get_guild_config(guild.id)
        if cfg["marriage_role"]:
            role = guild.get_role(cfg["marriage_role"])
            if role and role not in member.roles:
                try: await member.add_roles(role, reason="Гэрлэлт")
                except discord.HTTPException:
                    logger.warning("Could not grant marriage role to %s in guild %s", member.id, guild.id, exc_info=True)

    async def remove_marriage_role(self, guild, member):
        cfg = await self.get_guild_config(guild.id)
        if cfg["marriage_role"]:
            role = guild.get_role(cfg["marriage_role"])
            if role and role in member.roles:
                try: await member.remove_roles(role, reason="Салалт")
                except discord.HTTPException:
                    logger.warning("Could not remove marriage role from %s in guild %s", member.id, guild.id, exc_info=True)

    async def announce_marriage(self, guild, user1, user2):
        cfg = await self.get_guild_config(guild.id)
        if cfg["announce_channel"]:
            channel = guild.get_channel(cfg["announce_channel"])
            if channel:
                embed = discord.Embed(title="💒 Шинэ гэрлэлт!", description=f"{user1.mention} болон {user2.mention} гэрлэлээ!", color=LOVE_COLOR)
                await channel.send(embed=embed)

    async def announce_divorce(self, guild, user1, user2):
        cfg = await self.get_guild_config(guild.id)
        if cfg["announce_channel"]:
            channel = guild.get_channel(cfg["announce_channel"])
            if channel:
                embed = discord.Embed(title="💔 Салалт", description=f"{user1.mention} болон {user2.mention} саллаа.", color=ERROR_COLOR)
                await channel.send(embed=embed)

    # ═════════ ГЭРЛЭЛТ ═════════
    async def get_marriages(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "marriages", {"guild_id": str(guild_id)}
        )
        result = []
        seen_partners = set()
        # Each marriage is stored in both directions; prefer this user's row.
        for r in sorted(rows, key=lambda row: str(row.get("user_id")) != str(user_id)):
            uid = r.get("user_id")
            pid = r.get("partner_id")
            if str(uid) != str(user_id) and str(pid) != str(user_id):
                continue
            partner = pid if str(uid) == str(user_id) else uid
            if str(partner) in seen_partners:
                continue
            seen_partners.add(str(partner))
            result.append({"partner": int(partner), "love_points": r.get("love_points", 0) or 0,
                           "ring": f"{r.get('ring_emoji', '')} {r.get('ring_name', '')}".strip() if r.get("ring_emoji") else r.get("ring_name", ""),
                           "ring_name": r.get("ring_name"), "ring_emoji": r.get("ring_emoji", ""),
                           "marriage_date": r.get("marriage_date")})
        return result

    async def add_marriage(self, guild_id, u1, u2, ring_name, ring_emoji=""):
        mar_date = int(time.time())
        for a, b in [(u1, u2), (u2, u1)]:
            await self.bot.db_manager.insert("marriages", {
                "user_id": str(a), "partner_id": str(b), "guild_id": str(guild_id),
                "marriage_date": mar_date, "ring_name": ring_name, "ring_emoji": ring_emoji, "love_points": 0,
            })

    async def remove_marriage(self, guild_id, u1, u2):
        await self.bot.db_manager.delete(
            "marriages",
            {"guild_id": str(guild_id), "user_id": str(u1), "partner_id": str(u2)},
        )
        await self.bot.db_manager.delete(
            "marriages",
            {"guild_id": str(guild_id), "user_id": str(u2), "partner_id": str(u1)},
        )

    async def marriage_exists(self, guild_id, u1, u2):
        row = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(u1), "partner_id": str(u2)}
        )
        if row:
            return True
        row = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(u2), "partner_id": str(u1)}
        )
        return row is not None

    async def get_spouses(self, guild_id, user_id):
        return [m["partner"] for m in await self.get_marriages(guild_id, user_id)]

    # ═════════ ЭЦЭГ ЭХ / ХҮҮХЭД ═════════
    async def get_children(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(user_id)}
        )
        return [int(r["child_id"]) for r in rows]

    async def get_parents(self, guild_id, user_id):
        rows = await self.bot.db_manager.fetch_all(
            "adoptions", {"guild_id": str(guild_id), "child_id": str(user_id)}
        )
        return [int(r["parent_id"]) for r in rows]

    async def add_parent_child(self, guild_id, parent_id, child_id, rel_type="adoption"):
        await self.bot.db_manager.upsert(
            "adoptions",
            {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id),
             "type": rel_type, "adopted_since": int(time.time())},
            on_conflict="guild_id,parent_id,child_id",
        )

    async def remove_parent_child(self, guild_id, parent_id, child_id):
        await self.bot.db_manager.delete(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id)}
        )

    async def is_parent_child(self, guild_id, parent_id, child_id):
        row = await self.bot.db_manager.fetch_one(
            "adoptions", {"guild_id": str(guild_id), "parent_id": str(parent_id), "child_id": str(child_id)}
        )
        return row is not None

    async def add_family_relation(self, guild_id, user_id, relative_id, relation_type):
        reverse_type = FAMILY_RELATIONS[relation_type][1]
        now = int(time.time())
        for source, target, kind in (
            (user_id, relative_id, relation_type),
            (relative_id, user_id, reverse_type),
        ):
            await self.bot.db_manager.upsert(
                "family_relationships",
                {
                    "guild_id": str(guild_id),
                    "user_id": str(source),
                    "relative_id": str(target),
                    "relation_type": kind,
                    "created_at": now,
                },
                on_conflict="guild_id,user_id,relative_id",
            )

    async def get_family_relations(self, guild_id, user_id):
        return await self.bot.db_manager.fetch_all(
            "family_relationships", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )

    async def remove_family_relation(self, guild_id, user_id, relative_id):
        for source, target in ((user_id, relative_id), (relative_id, user_id)):
            await self.bot.db_manager.delete(
                "family_relationships",
                {"guild_id": str(guild_id), "user_id": str(source), "relative_id": str(target)},
            )

    # ═════════ БЛОК / АВТО ЗӨВШӨӨРӨЛ ═════════
    async def is_blocked(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return bool(row.get("blocked", 0)) if row else False

    async def set_blocked(self, guild_id, user_id, blocked):
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "blocked": int(blocked)},
            on_conflict="guild_id,user_id",
        )

    async def get_auto_accept(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return bool(row.get("auto_accept_marriage", 0)) if row else False

    async def set_auto_accept(self, guild_id, user_id, auto):
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "auto_accept_marriage": int(auto)},
            on_conflict="guild_id,user_id",
        )

    # ═════════ БЭЛЭГ / LOVE ═════════
    async def add_gift(self, guild_id, from_id, to_id, gift_type, love):
        await self.bot.db_manager.insert("marriage_gifts", {
            "guild_id": str(guild_id), "from_id": str(from_id), "to_id": str(to_id),
            "gift_type": gift_type, "love_points": love, "given_at": int(time.time()),
        })
        marriage = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild_id), "user_id": str(from_id), "partner_id": str(to_id)}
        )
        if not marriage:
            marriage = await self.bot.db_manager.fetch_one(
                "marriages", {"guild_id": str(guild_id), "user_id": str(to_id), "partner_id": str(from_id)}
            )
        if marriage:
            await self.bot.db_manager.update(
                "marriages",
                {"guild_id": str(guild_id), "user_id": str(from_id), "partner_id": str(to_id)},
                {"love_points": (marriage.get("love_points", 0) or 0) + love},
            )

    async def get_anniversary(self, marriage_date):
        if not marriage_date: return None
        try: marriage_date = int(marriage_date)
        except (TypeError, ValueError): return None
        today = datetime.datetime.now(datetime.UTC).date()
        try:
            mar_date = datetime.datetime.fromtimestamp(marriage_date, datetime.UTC).date()
        except (OverflowError, OSError, ValueError):
            return None
        days = (today - mar_date).days
        def anniversary(year):
            try:
                return datetime.date(year, mar_date.month, mar_date.day)
            except ValueError:
                # A leap-day marriage observes February 28 in non-leap years.
                return datetime.date(year, 2, 28)
        next_ann = anniversary(today.year)
        if next_ann < today: next_ann = anniversary(today.year + 1)
        return {"days": days, "next_days": (next_ann - today).days, "date": mar_date.strftime("%Y-%m-%d")}

    async def get_last_gift_time(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return row.get("last_gift_daily", 0) if row else 0

    async def update_last_gift_time(self, guild_id, user_id):
        now = int(time.time())
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "last_gift_daily": now},
            on_conflict="guild_id,user_id",
        )

    async def get_last_love_time(self, guild_id, user_id):
        row = await self.bot.db_manager.fetch_one(
            "marriage_user_settings", {"guild_id": str(guild_id), "user_id": str(user_id)}
        )
        return row.get("last_love_daily", 0) if row else 0

    async def update_last_love_time(self, guild_id, user_id):
        now = int(time.time())
        await self.bot.db_manager.upsert(
            "marriage_user_settings",
            {"guild_id": str(guild_id), "user_id": str(user_id), "last_love_daily": now},
            on_conflict="guild_id,user_id",
        )

    # ═════════ ЗУРАГ ТАТАХ ═════════
    async def _download_avatar(self, sess, url, size):
        try:
            async with sess.get(url) as resp:
                # Response-ийн хэмжээг хязгаарлана.
                data = await resp.content.read(MAX_AVATAR_BYTES + 1)
                if len(data) > MAX_AVATAR_BYTES:
                    raise ValueError("avatar response too large")
            img = Image.open(io.BytesIO(data)).convert("RGBA").resize((size, size))
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError):
            logger.warning("Could not load marriage card avatar", exc_info=True)
            img = Image.new("RGBA", (size, size), (88, 101, 242, 255))
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        img.putalpha(mask)
        return img

    # ═════════ SLASH COMMANDS (ГРУПП) ═════════
    marriage_group = app_commands.Group(name="marriage", description="Гэрлэлт, гэр бүлийн командууд", guild_only=True)

    @marriage_group.command(name="guide", description="Marriage системийн товч заавар")
    async def slash_guide(self, interaction: discord.Interaction):
        view = MarriageHubView(self, interaction.guild_id, interaction.user.id)
        await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

    @marriage_group.command(name="propose", description="Гэрлэх санал тавих")
    @app_commands.describe(user="Гэрлэх санал тавих хэрэглэгч")
    async def slash_propose(self, interaction: discord.Interaction, user: discord.Member):
        await self._propose(interaction, user, is_slash=True)

    @marriage_group.command(name="divorce", description="Гэрлэлтийг цуцлах")
    @app_commands.describe(user="Цуцлах хэрэглэгч (хоосон орхивол бүгдийг)")
    async def slash_divorce(self, interaction: discord.Interaction, user: discord.Member | None = None):
        await self._divorce(interaction, user, is_slash=True)

    @marriage_group.command(name="adopt", description="Хүүхэд өргөмжлөх")
    @app_commands.describe(child="Хүүхдээр сонгох хэрэглэгч", child_role="Хүү эсвэл охин")
    @app_commands.choices(child_role=[
        app_commands.Choice(name="👦 Хүү", value="son"),
        app_commands.Choice(name="👧 Охин", value="daughter"),
    ])
    async def slash_adopt(self, interaction: discord.Interaction, child: discord.Member, child_role: str):
        await self._adopt(interaction, child, child_role=child_role, is_slash=True)

    @marriage_group.command(name="request-parent", description="Эцэг эх болох санал тавих")
    @app_commands.describe(parent="Эцэг эхээр сонгох хэрэглэгч", parent_role="Аав эсвэл ээж")
    @app_commands.choices(parent_role=[
        app_commands.Choice(name="👨 Аав", value="father"),
        app_commands.Choice(name="👩 Ээж", value="mother"),
    ])
    async def slash_request_parent(self, interaction: discord.Interaction, parent: discord.Member, parent_role: str):
        await self._makeparent(interaction, parent, parent_role=parent_role, is_slash=True)

    @marriage_group.command(name="leave-family", description="Эцэг эхийн холбоог цуцлах")
    async def slash_leave_family(self, interaction: discord.Interaction):
        await self._runaway(interaction, is_slash=True)

    @marriage_group.command(name="family", description="Хань, эцэг эх, хүүхдүүдээ нэг дор харах")
    @app_commands.describe(member="Хэний гэр бүл (хоосон орхивол өөрийн)")
    async def slash_family(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._family_overview(interaction, member, is_slash=True)

    @marriage_group.command(name="tree", description="Гэр бүлийн мод (зураг)")
    @app_commands.describe(member="Хэнийх (хоосон орхивол өөрийн)")
    async def slash_tree(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._family_tree(interaction, member, is_slash=True)

    @marriage_group.command(name="relationship", description="Хоёр хэрэглэгчийн хоорондын харилцаа")
    @app_commands.describe(user1="Эхний хэрэглэгч", user2="Хоёр дахь хэрэглэгч")
    async def slash_relationship(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        await self._relationship(interaction, user1, user2, is_slash=True)

    @marriage_group.command(name="disown", description="Хүүхдээсээ татгалзах")
    @app_commands.describe(child="Татгалзах хүүхэд")
    async def slash_disown(self, interaction: discord.Interaction, child: discord.Member):
        await self._disown(interaction, child, is_slash=True)

    @marriage_group.command(name="love", description="Хэрэглэгчид love оноо өгөх")
    @app_commands.describe(target="Love оноо өгөх хэрэглэгч")
    async def slash_love(self, interaction: discord.Interaction, target: discord.Member):
        await self._love(interaction, target, is_slash=True)

    @marriage_group.command(name="gift", description="Ханьдаа бэлэг өгөх")
    @app_commands.choices(gift_type=[app_commands.Choice(name=v["name"], value=k) for k, v in GIFTS.items()])
    async def slash_gift(self, interaction: discord.Interaction, gift_type: str):
        await self._gift(interaction, gift_type, is_slash=True)

    @marriage_group.command(name="profile", description="Гэрлэлтийн зурагт карт үүсгэх")
    @app_commands.describe(member="Хэний карт (хоосон орхивол өөрийн)")
    async def slash_profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await self._marriage_card(interaction, member, is_slash=True)

    @marriage_group.command(name="privacy", description="Гэрлэх санал хүлээн авах эсэх")
    @app_commands.describe(allow_proposals="Бусдаас гэрлэх санал авах")
    async def slash_privacy(self, interaction: discord.Interaction, allow_proposals: bool):
        await self.set_blocked(interaction.guild.id, interaction.user.id, not allow_proposals)
        await interaction.response.send_message(
            f"🔐 Гэрлэх санал: **{'НЭЭЛТТЭЙ' if allow_proposals else 'ХААЛТТАЙ'}**",
            ephemeral=True,
        )

    @marriage_group.command(name="setup", description="Гэрлэлтийн тохиргооны самбар нээх")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_setup(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg = await self.get_guild_config(interaction.guild_id)
        view = MarriageSetupView(self, interaction.guild_id, interaction.user.id)
        embed = view.build_embed(cfg, interaction.guild)
        view.message = await interaction.followup.send(embed=embed, view=view, ephemeral=True, wait=True)

    # ═════════ БҮХ ҮЙЛДЛИЙН ТӨВ ФУНКЦУУД ═════════
    async def _propose(self, ctx_or_inter, user, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if user.bot or user.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Өөртөө эсвэл ботод санал тавьж болохгүй.", is_slash=is_slash)
        cfg = await self.get_guild_config(guild.id)
        if not cfg["enabled"]:
            return await self._reply(ctx_or_inter, "❌ Гэрлэлтийн систем идэвхгүй.", is_slash=is_slash)
        if await self.marriage_exists(guild.id, author.id, user.id):
            return await self._reply(ctx_or_inter, "❌ Та аль хэдийн энэ хүнтэй гэрлэсэн.", is_slash=is_slash)
        spouses = await self.get_spouses(guild.id, author.id)
        if not cfg["polygamy"] and len(spouses) >= 1:
            return await self._reply(ctx_or_inter, "❌ Полигами зөвшөөрөгдөөгүй.", is_slash=is_slash)
        if len(spouses) >= cfg["max_spouses"]:
            return await self._reply(ctx_or_inter, f"❌ Хамгийн ихдээ {cfg['max_spouses']} хүнтэй гэрлэх боломжтой.", is_slash=is_slash)
        if await self.is_blocked(guild.id, user.id):
            return await self._reply(ctx_or_inter, f"🚫 {user.mention} гэрлэх санал авахаас татгалзсан.", is_slash=is_slash)
        shop = self.bot.get_cog("ShopCog")
        ring_item_id, ring_name, ring_emoji = None, None, None
        if shop:
            inv = await shop.get_user_inventory(author.id, guild.id)
            for item_id in inv:
                if await self._is_ring_item(item_id):
                    item = await shop.get_item(item_id)
                    if item:
                        ring_item_id, ring_name, ring_emoji = item_id, item.get("name", "Энгийн бөгж"), item.get("emoji", "💍")
                        break
            if not ring_item_id:
                return await self._reply(ctx_or_inter, "❌ Инвентарт гэрлэх бөгж байхгүй.", is_slash=is_slash)
        else:
            return await self._reply(ctx_or_inter, "❌ Дэлгүүрийн систем ачаалагдаагүй.", is_slash=is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(user.id),
             "proposal_type": "marriage", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="💍 ГЭРЛЭХ САНАЛ",
                              description=f"{author.mention} {user.mention}-д гэрлэх санал тавьж байна!\n\n💍 Бөгж: {ring_emoji} **{ring_name}**\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=GOLD_COLOR)
        view = ProposalView(self, guild.id, author.id, user.id, ring_name, ring_emoji, ring_item_id)
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=user.mention, embed=embed, view=view)

    async def _divorce(self, ctx_or_inter, user, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if user is None:
            marriages = await self.get_marriages(guild.id, author.id)
            if not marriages:
                return await self._reply(ctx_or_inter, "❌ Танд гэрлэлт байхгүй.", is_slash=is_slash)
            for m in marriages:
                partner = guild.get_member(m["partner"])
                await self.remove_marriage(guild.id, author.id, m["partner"])
                await self.remove_marriage_role(guild, author)
                if partner: await self.remove_marriage_role(guild, partner)
            return await self._reply(ctx_or_inter, "💔 Бүх гэрлэлтийг цуцаллаа.", is_slash=is_slash)
        else:
            if not await self.marriage_exists(guild.id, author.id, user.id):
                return await self._reply(ctx_or_inter, f"❌ Та {user.mention}-тэй гэрлээгүй байна.", is_slash=is_slash)
            await self.remove_marriage(guild.id, author.id, user.id)
            await self.remove_marriage_role(guild, author)
            await self.remove_marriage_role(guild, user)
            await self.announce_divorce(guild, author, user)
            return await self._reply(ctx_or_inter, f"💔 {author.mention} болон {user.mention} саллаа.", is_slash=is_slash)

    async def _adopt(self, ctx_or_inter, child, child_role="child", is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if child.bot or child.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Бот эсвэл өөрийгөө өргөмжлөх боломжгүй.", is_slash=is_slash)
        if await self.is_parent_child(guild.id, author.id, child.id):
            return await self._reply(ctx_or_inter, f"❌ {child.mention} аль хэдийн таны хүүхэд.", is_slash=is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(child.id),
             "proposal_type": "adoption", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="👶 ХҮҮХЭД ӨРГӨМЖЛӨХ САНАЛ",
                              description=f"{author.mention} {child.mention}-г хүүхэд болгон өргөмжлөх санал тавьж байна!\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=PURPLE_COLOR)
        view = AdoptView(
            self.bot, guild.id, author.id, child.id, "adoption",
            relationship_type=f"parent-{child_role}",
        )
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=child.mention, embed=embed, view=view)

    async def _disown(self, ctx_or_inter, child, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if not await self.is_parent_child(guild.id, author.id, child.id):
            return await self._reply(ctx_or_inter, f"❌ {child.mention} таны хүүхэд биш.", is_slash=is_slash)
        await self.remove_parent_child(guild.id, author.id, child.id)
        return await self._reply(ctx_or_inter, f"💔 {author.mention} {child.mention} -аас татгалзлаа.", is_slash=is_slash)

    async def _makeparent(self, ctx_or_inter, parent, parent_role="parent", is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if parent.bot or parent.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Бот эсвэл өөрийгөө эцэг эх болгох боломжгүй.", is_slash=is_slash)
        if await self.is_parent_child(guild.id, parent.id, author.id):
            return await self._reply(ctx_or_inter, f"❌ {parent.mention} аль хэдийн таны эцэг эх.", is_slash=is_slash)
        expires = int(time.time()) + PROPOSAL_TIMEOUT
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {"guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(parent.id),
             "proposal_type": "parenthood", "ring_id": 0, "expires_at": expires},
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        embed = discord.Embed(title="👪 ЭЦЭГ ЭХ БОЛОХ САНАЛ",
                              description=f"{author.mention} {parent.mention}-г эцэг эхээр сонгохыг хүсч байна!\n\n{PROPOSAL_TIMEOUT} секундын дотор зөвшөөрөх эсвэл татгалзах боломжтой.",
                              color=PURPLE_COLOR)
        view = AdoptView(
            self.bot, guild.id, parent.id, author.id, "parenthood",
            relationship_type=f"{parent_role}-child",
        )
        if is_slash:
            await ctx_or_inter.response.send_message(embed=embed, view=view)
            view.message = await ctx_or_inter.original_response()
        else:
            view.message = await ctx_or_inter.send(content=parent.mention, embed=embed, view=view)

    async def _runaway(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        parents = await self.get_parents(guild.id, author.id)
        if not parents:
            return await self._reply(ctx_or_inter, "❌ Танд эцэг эх байхгүй.", is_slash=is_slash)
        for parent_id in parents:
            await self.remove_parent_child(guild.id, parent_id, author.id)
        return await self._reply(ctx_or_inter, "🏃 Зугтлаа! Эцэг эхийн харилцаа цуцлагдлаа.", is_slash=is_slash)

    async def _request_family_relation(self, ctx_or_inter, target, relation_type, is_slash=False):
        author = ctx_or_inter.user if is_slash else ctx_or_inter.author
        guild = ctx_or_inter.guild
        if target.bot or target.id == author.id:
            return await self._reply(ctx_or_inter, "❌ Өөрийгөө эсвэл ботыг сонгох боломжгүй.", is_slash=is_slash)
        if relation_type not in FAMILY_RELATIONS:
            return await self._reply(ctx_or_inter, "❌ Холбооны төрөл буруу байна.", is_slash=is_slash)
        existing = await self.get_family_relations(guild.id, author.id)
        if any(int(row["relative_id"]) == target.id for row in existing):
            return await self._reply(ctx_or_inter, "❌ Энэ хүнтэй гэр бүлийн холбоо аль хэдийн байна.", is_slash=is_slash)
        proposal_type = f"family_{relation_type}"
        await self.bot.db_manager.upsert(
            "marriage_proposals",
            {
                "guild_id": str(guild.id), "from_id": str(author.id), "to_id": str(target.id),
                "proposal_type": proposal_type, "ring_id": 0,
                "expires_at": int(time.time()) + PROPOSAL_TIMEOUT,
            },
            on_conflict="guild_id,from_id,to_id,proposal_type",
        )
        relation = family_relation_label(relation_type)
        embed = discord.Embed(
            title="👨‍👩‍👧‍👦 ГЭР БҮЛИЙН ХҮСЭЛТ",
            description=(f"{author.mention} таныг **{relation}** болгох хүсэлт явууллаа.\n"
                         f"{PROPOSAL_TIMEOUT} секундын дотор хариулна уу."),
            color=PURPLE_COLOR,
        )
        view = FamilyRelationRequestView(self, guild.id, author.id, target.id, relation_type)
        await ctx_or_inter.response.send_message(content=target.mention, embed=embed, view=view)
        view.message = await ctx_or_inter.original_response()

    async def _remove_family_relation(self, ctx_or_inter, target, is_slash=False):
        author = ctx_or_inter.user if is_slash else ctx_or_inter.author
        guild = ctx_or_inter.guild
        removed = False
        if await self.marriage_exists(guild.id, author.id, target.id):
            await self.remove_marriage(guild.id, author.id, target.id)
            removed = True
        relations = await self.get_family_relations(guild.id, author.id)
        if any(int(row["relative_id"]) == target.id for row in relations):
            await self.remove_family_relation(guild.id, author.id, target.id)
            removed = True
        message = "✂️ Гэр бүлийн холбоог хоёр талаас салгалаа." if removed else "❌ Энэ хүнтэй холбоо олдсонгүй."
        await self._reply(ctx_or_inter, message, is_slash=is_slash)

    async def _spouse(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        spouses = await self.get_spouses(guild.id, author.id)
        if not spouses:
            return await self._reply(ctx_or_inter, "❌ Та гэрлээгүй байна.", is_slash=is_slash)
        partners = [guild.get_member(sid).mention if guild.get_member(sid) else f"<@{sid}>" for sid in spouses]
        # ЗАСВАР: embed аргументын дараа is_slash-г нэртэй дамжуулах
        await self._reply(ctx_or_inter, embed=discord.Embed(title="💑 ХАМТРАГЧ(ИД)", description=", ".join(partners), color=LOVE_COLOR), is_slash=is_slash)

    async def _parent(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        parents = await self.get_parents(guild.id, author.id)
        if not parents:
            return await self._reply(ctx_or_inter, "❌ Танд эцэг эх байхгүй.", is_slash=is_slash)
        parts = [guild.get_member(pid).mention if guild.get_member(pid) else f"<@{pid}>" for pid in parents]
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=discord.Embed(title="👪 ЭЦЭГ ЭХ", description=", ".join(parts), color=INFO_COLOR), is_slash=is_slash)

    async def _children(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        children = await self.get_children(guild.id, author.id)
        if not children:
            return await self._reply(ctx_or_inter, "❌ Танд хүүхэд байхгүй.", is_slash=is_slash)
        parts = [guild.get_member(cid).mention if guild.get_member(cid) else f"<@{cid}>" for cid in children]
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=discord.Embed(title="👶 ХҮҮХДҮҮД", description=", ".join(parts), color=INFO_COLOR), is_slash=is_slash)

    async def _love(self, ctx_or_inter, target, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        if not await self.marriage_exists(guild.id, author.id, target.id):
            return await self._reply(ctx_or_inter, f"❌ {target.mention} -тай гэрлээгүй байна.", is_slash=is_slash)
        last = await self.get_last_love_time(guild.id, author.id)
        if last and int(time.time()) - last < 86400:
            remaining = int(86400 - (time.time() - last))
            hours, minutes = divmod(remaining // 60, 60)
            return await self._reply(ctx_or_inter, f"⏰ Өдөрт 1 удаа love бэлэглэх боломжтой. Үлдсэн: {hours}ц {minutes}м", is_slash=is_slash)
        marriage = await self.bot.db_manager.fetch_one(
            "marriages", {"guild_id": str(guild.id), "user_id": str(author.id), "partner_id": str(target.id)}
        )
        if not marriage:
            marriage = await self.bot.db_manager.fetch_one(
                "marriages", {"guild_id": str(guild.id), "user_id": str(target.id), "partner_id": str(author.id)}
            )
        if marriage:
            await self.bot.db_manager.update(
                "marriages",
                {"guild_id": str(guild.id), "user_id": str(author.id), "partner_id": str(target.id)},
                {"love_points": (marriage.get("love_points", 0) or 0) + 10},
            )
        await self.update_last_love_time(guild.id, author.id)
        await self._reply(ctx_or_inter, f"💖 {author.mention} {target.mention} -д 10 love оноо бэлэглэлээ!", is_slash=is_slash)

    async def _gift(self, ctx_or_inter, gift_type, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        gift = GIFTS.get(gift_type)
        if not gift:
            return await self._reply(ctx_or_inter, "❌ Бэлэг олдсонгүй.", is_slash=is_slash)
        spouses = await self.get_spouses(guild.id, author.id)
        if not spouses:
            return await self._reply(ctx_or_inter, "❌ Танд хань байхгүй.", is_slash=is_slash)
        last = await self.get_last_gift_time(guild.id, author.id)
        if last and int(time.time()) - last < 86400:
            return await self._reply(ctx_or_inter, "❌ Өнөөдөр аль хэдийн бэлэг өгсөн. 24 цаг хүлээнэ үү.", is_slash=is_slash)
        partner_id = spouses[0]
        shop = self.bot.get_cog("ShopCog")
        if shop:
            await shop.add_item(partner_id, guild.id, gift.get("item_id", 0), 1)
        await self.add_gift(guild.id, author.id, partner_id, gift_type, gift["love"])
        await self.update_last_gift_time(guild.id, author.id)
        await self._reply(ctx_or_inter, f"🎁 {author.mention} ханьдаа {gift['emoji']} **{gift['name']}** бэлэглэж, +{gift['love']}❤️ хайрын оноо нэмлээ!", is_slash=is_slash)

    async def _family_overview(self, ctx_or_inter, member=None, is_slash=False):
        guild = ctx_or_inter.guild
        target = member or (ctx_or_inter.user if is_slash else ctx_or_inter.author)
        spouses = await self.get_spouses(guild.id, target.id)
        parents = await self.get_parents(guild.id, target.id)
        children = await self.get_children(guild.id, target.id)
        custom_relations = await self.get_family_relations(guild.id, target.id)

        def mentions(ids):
            return ", ".join(
                guild.get_member(user_id).mention if guild.get_member(user_id) else f"<@{user_id}>"
                for user_id in ids
            ) or "Байхгүй"

        embed = discord.Embed(
            title=f"👨‍👩‍👧‍👦 {target.display_name} — Гэр бүл",
            description=(
                f"Нийт **{1 + len(set(spouses + parents + children + [int(row['relative_id']) for row in custom_relations]))}** гишүүн"
            ),
            color=LOVE_COLOR,
        )
        embed.add_field(name=f"💑 Хань · {len(spouses)}", value=mentions(spouses), inline=False)
        embed.add_field(name=f"👪 Эцэг эх · {len(parents)}", value=mentions(parents), inline=False)
        embed.add_field(name=f"👶 Хүүхэд · {len(children)}", value=mentions(children), inline=False)
        grouped = {}
        for row in custom_relations:
            grouped.setdefault(row.get("relation_type", "family"), []).append(int(row["relative_id"]))
        for relation_type, ids in grouped.items():
            embed.add_field(
                name=f"{family_relation_label(relation_type)} · {len(ids)}",
                value=mentions(ids),
                inline=False,
            )
        embed.set_footer(text="Зурагт мод: /marriage tree • Карт: /marriage profile")
        await self._reply(ctx_or_inter, embed=embed, is_slash=is_slash)

    async def _family_tree(self, ctx_or_inter, member=None, full=False, is_slash=False):
        if is_slash:
            target = member or ctx_or_inter.user
            guild = ctx_or_inter.guild
            await ctx_or_inter.response.defer()
        else:
            target = member or ctx_or_inter.author
            guild = ctx_or_inter.guild
            await ctx_or_inter.defer() if hasattr(ctx_or_inter, 'defer') else None

        spouses_ids = await self.get_spouses(guild.id, target.id)
        children_ids = await self.get_children(guild.id, target.id)
        parents_ids = await self.get_parents(guild.id, target.id)

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as sess:
            main_url = target.display_avatar.replace(size=256, format="png").url
            ava_main = await self._download_avatar(sess, main_url, 160)

            async def fetch_ava_list(members):
                avas = []
                for mem, uid in members[:8]:
                    url = mem.display_avatar.replace(size=256, format="png").url if mem else None
                    if url:
                        ava = await self._download_avatar(sess, url, 80)
                        name = mem.display_name if mem else f"<@{uid}>"
                        avas.append((ava, name))
                return avas

            spouse_avas = await fetch_ava_list([(guild.get_member(sid), sid) for sid in spouses_ids])
            child_avas = await fetch_ava_list([(guild.get_member(cid), cid) for cid in children_ids])
            parent_avas = await fetch_ava_list([(guild.get_member(pid), pid) for pid in parents_ids])

        buf = await asyncio.to_thread(
            self._render_family_card, target, spouses_ids, children_ids, parents_ids,
            ava_main, spouse_avas[:4], child_avas[:4], parent_avas[:4]
        )
        embed = discord.Embed(color=SUCCESS_COLOR)
        embed.set_image(url="attachment://family_tree.png")
        embed.set_footer(text=f"{guild.name} • Гэр бүлийн мод")
        file = discord.File(buf, filename="family_tree.png")
        if is_slash:
            await ctx_or_inter.edit_original_response(embed=embed, attachments=[file])
        else:
            await ctx_or_inter.send(embed=embed, file=file)

    async def _marriage_card(self, ctx_or_inter, member=None, is_slash=False):
        if is_slash:
            target = member or ctx_or_inter.user
            guild = ctx_or_inter.guild
            await ctx_or_inter.response.defer()
        else:
            target = member or ctx_or_inter.author
            guild = ctx_or_inter.guild
            await ctx_or_inter.defer() if hasattr(ctx_or_inter, 'defer') else None
        buf = await self._build_marriage_card(target, guild)
        if buf is None:
            embed = discord.Embed(title="💔 Гэрлээгүй", description="Энэ хэрэглэгч гэрлээгүй байна.", color=ERROR_COLOR)
            if is_slash:
                await ctx_or_inter.edit_original_response(embed=embed)
            else:
                await ctx_or_inter.send(embed=embed)
            return
        embed = discord.Embed(color=LOVE_COLOR)
        embed.set_image(url="attachment://marriage_card.png")
        file = discord.File(buf, filename="marriage_card.png")
        if is_slash:
            await ctx_or_inter.edit_original_response(embed=embed, attachments=[file])
        else:
            await ctx_or_inter.send(embed=embed, file=file)

    async def _relationship(self, ctx_or_inter, user1, user2, is_slash=False):
        guild = ctx_or_inter.guild
        family_rows = await self.get_family_relations(guild.id, user1.id)
        family_match = next(
            (row for row in family_rows if int(row["relative_id"]) == user2.id),
            None,
        )
        if await self.marriage_exists(guild.id, user1.id, user2.id):
            rel = "💑 Хань"
        elif family_match:
            rel = family_relation_label(family_match["relation_type"])
        elif await self.is_parent_child(guild.id, user1.id, user2.id):
            rel = "👪 Эцэг эх (та түүний эцэг эх)"
        elif await self.is_parent_child(guild.id, user2.id, user1.id):
            rel = "👶 Хүүхэд (тэр таны эцэг эх)"
        else:
            rel = "❓ Харилцаагүй"
        embed = discord.Embed(title="🔗 ХАРИЛЦАА", description=f"**{user1.display_name}** ↔ **{user2.display_name}**\n{rel}", color=INFO_COLOR)
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=embed, is_slash=is_slash)

    async def _familysize(self, ctx_or_inter, is_slash=False):
        author = ctx_or_inter.author if hasattr(ctx_or_inter, 'author') else ctx_or_inter.user
        guild = ctx_or_inter.guild
        spouses = len(await self.get_spouses(guild.id, author.id))
        children = len(await self.get_children(guild.id, author.id))
        parents = len(await self.get_parents(guild.id, author.id))
        total = spouses + children + parents + 1
        embed = discord.Embed(title="👨‍👩‍👧‍👦 ГЭР БҮЛИЙН ХЭМЖЭЭ",
                              description=f"**{author.display_name}**-ын гэр бүл:\n"
                                          f"💑 Хань: {spouses}\n"
                                          f"👶 Хүүхэд: {children}\n"
                                          f"👪 Эцэг эх: {parents}\n"
                                          f"✨ Нийт: {total}",
                              color=INFO_COLOR)
        # ЗАСВАР
        await self._reply(ctx_or_inter, embed=embed, is_slash=is_slash)

    async def _reply(self, ctx_or_inter, content=None, embed=None, is_slash=False):
        if is_slash:
            if not ctx_or_inter.response.is_done():
                await ctx_or_inter.response.send_message(content=content, embed=embed, ephemeral=True)
            else:
                await ctx_or_inter.followup.send(content=content, embed=embed, ephemeral=True)
        else:
            if hasattr(ctx_or_inter, 'response') and isinstance(ctx_or_inter, discord.Interaction):
                if not ctx_or_inter.response.is_done():
                    await ctx_or_inter.response.send_message(content=content, embed=embed)
                else:
                    await ctx_or_inter.followup.send(content=content, embed=embed)
            elif content:
                await ctx_or_inter.send(content=content, embed=embed)
            else:
                await ctx_or_inter.send(embed=embed)

    async def _is_ring_item(self, item_id):
        shop = self.bot.get_cog("ShopCog")
        if not shop: return False
        item = await shop.get_item(item_id)
        return item is not None and item.get("category") == "ring"

    async def _build_marriage_card(self, member, guild):
        marriages = await self.get_marriages(guild.id, member.id)
        if not marriages: return None
        partner_id = marriages[0]["partner"]
        partner = guild.get_member(partner_id)
        love = marriages[0]["love_points"]
        ring = marriages[0]["ring"]
        raw_date = marriages[0]["marriage_date"]
        anniv = await self.get_anniversary(int(raw_date) if raw_date else None)
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as sess:
            url1 = member.display_avatar.replace(size=256, format="png").url
            url2 = partner.display_avatar.replace(size=256, format="png").url if partner else None
            ava1 = await self._download_avatar(sess, url1, 180)
            ava2 = await self._download_avatar(sess, url2, 180) if url2 else None
        return await asyncio.to_thread(self._render_marriage_card, member, partner, love, ring, anniv, ava1, ava2)

    # ═════════ ЗУРГИЙН ФУНКЦУУД ═════════
    def _render_family_card(self, member, spouses_ids, children_ids, parents_ids, ava_main, spouse_avas, child_avas, parent_avas):
        W, H = 1150, 780
        seed = int(getattr(member, "id", 7)) % 100000
        img = journal.parchment((W, H), seed=seed)
        draw = ImageDraw.Draw(img)
        journal.ink_border(draw, (W, H), seed=seed + 1)

        font_title = _load_font(32, True)
        font_name = _load_font(20, True)
        font_main_name = _load_font(28, True)
        font_small = _load_font(15, False)

        journal.banner(draw, (190, 32, 960, 88), "STARLIGHT BONDS", font_title, seed=seed + 2)
        draw_text_with_fallback(draw, (W // 2 - 85, 94), "ГЭР БҮЛИЙН МОД", font_small,
                                fill=journal.INK_SOFT, size=15, bold=True)

        def draw_person(cx, y, size, ava, name, name_font=font_name, nsize=20):
            bx = cx - size // 2
            journal.sketch_frame(img, (bx, y, bx + size, y + size), ava, seed=seed + cx % 97)
            if name:
                nm = str(name)[:18]
                w = draw.textlength(nm, font=name_font)
                draw_text_with_fallback(draw, (cx - w / 2, y + size + 8), nm, name_font,
                                        fill=journal.INK, size=nsize, bold=True)

        def link(x0, y0, x1, y1, seedk=70):
            journal.wobble_line(draw, (x0, y0), (x1, y1), journal.INK_FAINT, 2, seed + seedk, amp=2.2, segs=18)

        mx = W // 2

        parent_positions = (mx - 210, mx + 130)
        spouse_positions = (mx - 380, mx + 380)
        children = list(child_avas)[:5]

        for i, (ava, name) in enumerate(parent_avas[:2]):
            draw_person(parent_positions[i], 116, 78, ava, name, font_name, 16)
            link(parent_positions[i], 194, mx, 232, 80 + i)

        draw_person(mx, 232, 176, ava_main, member.display_name[:22], font_main_name, 26)

        for i, (ava, name) in enumerate(spouse_avas[:2]):
            draw_person(spouse_positions[i], 272, 86, ava, name, font_name, 16)
            dirn = -1 if i == 0 else 1
            link(spouse_positions[i] - dirn * 43, 315, mx + dirn * 88, 320, 90 + i)

        if children:
            gap = (W - 220) // len(children)
            for i, (ava, name) in enumerate(children):
                cx = 110 + gap * i + gap // 2
                draw_person(cx, 610, 86, ava, name, font_name, 15)
                link(cx, 610, mx, 408, 100 + i)

        footer = "💞 " + member.display_name[:16]
        journal.twine_tag(draw, 60, H - 42, footer, font_small, color=(150, 148, 140, 255))
        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); buf.seek(0)
        return buf

    def _render_marriage_card(self, member, partner, love, ring, anniv, ava1, ava2):
        W, H = 1200, 660
        seed = int(getattr(member, "id", 7)) % 100000
        img = journal.parchment((W, H), seed=seed)
        draw = ImageDraw.Draw(img)
        journal.ink_border(draw, (W, H), seed=seed + 1)

        font_title = _load_font(32, True)
        font_name = _load_font(30, True)
        font_cap = _load_font(20, False)
        font_big = _load_font(44, True)
        font_mid = _load_font(30, True)
        font_small = _load_font(19, False)
        font_tiny = _load_font(15, False)

        def ctext(text, y, font, fill=journal.INK):
            w = draw.textlength(text, font=font)
            x0 = W // 2 - w / 2
            draw_text_with_fallback(draw, (x0, y), text, font, fill=fill,
                                    size=font.size, bold=True)
            return x0

        def sub_text(text, cx, y, font, fill=journal.INK_SOFT):
            w = draw.textlength(text, font=font)
            draw_text_with_fallback(draw, (cx - w / 2, y), text, font, fill=fill,
                                    size=font.size, bold=False)

        # ── Title banner ──
        journal.banner(draw, (150, 34, 1050, 92), "STARLIGHT BONDS", font_title, seed=seed + 2)
        ctext("ГЭРЛЭЛТИЙН ГЭРЧИЛГЭЭ", 100, font_cap, fill=journal.INK_SOFT)

        # ── Portraits ──
        journal.sketch_frame(img, (108, 160, 298, 350), ava1, seed=seed + 3)
        name1 = member.display_name[:20]
        w1 = draw.textlength(name1, font=font_name)
        draw_text_with_fallback(draw, (203 - w1 / 2, 362), name1, font_name,
                                fill=journal.INK, size=30, bold=True)
        date_str = ""
        if anniv:
            date_str = str(anniv.get("date", "")).replace("-", ".")
        sub_text("Гэрлэсэн: " + date_str, 203, 404, font_cap)

        if ava2:
            journal.sketch_frame(img, (902, 160, 1092, 350), ava2, seed=seed + 4)
        if partner:
            name2 = partner.display_name[:20]
            w2 = draw.textlength(name2, font=font_name)
            draw_text_with_fallback(draw, (997 - w2 / 2, 362), name2, font_name,
                                    fill=journal.INK, size=30, bold=True)
        sub_text(str(ring) if ring else "Бөгжгүй", 997, 404, font_cap)

        journal.wobble_line(draw, (360, 148), (360, 505), journal.INK_SOFT, 2, seed + 5, amp=1.4)
        journal.wobble_line(draw, (840, 148), (840, 505), journal.INK_SOFT, 2, seed + 6, amp=1.4)

        # ── Heart ──
        cx, cy, s = 600, 215, 5.2
        pts = []
        for i in range(72):
            t = 2 * math.pi * i / 72
            x = 16 * math.sin(t) ** 3
            y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append((cx + x * s, cy - y * s))
        draw.polygon(pts, fill=(232, 92, 112, 255), outline=journal.WAX_DARK)
        draw.ellipse([cx - 28, cy - 46, cx - 12, cy - 30], fill=(255, 182, 189, 180))

        # ── Love level ──
        love_level = max(1, love // 100 + 1)
        ctext(f"⚡ Love Lv. {love_level}", 330, font_big)
        progress = (love % 100) / 100.0
        journal.watercolor_bar(draw, (400, 392, 800, 412), progress,
                               fill_from=(238, 184, 96, 255), fill_to=(226, 92, 112, 255), seed=seed + 7)
        rem = 100 - (love % 100)
        ctext(f"{rem} XP  →  Lv. {love_level + 1}", 420, font_tiny, fill=journal.INK_FAINT)

        # ── Married time ──
        if anniv:
            ctext(f"✨ {anniv['days']} хоног хамт", 458, font_mid)
            ctext(f"Дараагийн ой — {anniv['next_days']} өдрийн дараа", 496, font_small, fill=journal.INK_SOFT)
        else:
            ctext("✨ Дөнгөж гэрлэсэн", 458, font_mid)

        # ── Interlocking rings emblem ──
        ring_y = 590
        rbox_a = [600 - 30 - 6, ring_y - 30, 600 + 30 - 6, ring_y + 30]
        rbox_b = [600 - 30 + 6, ring_y - 30, 600 + 30 + 6, ring_y + 30]
        draw.ellipse(rbox_a, outline=journal.GOLD, width=9)
        draw.ellipse(rbox_b, outline=(226, 92, 112, 255), width=9)
        draw.arc(rbox_a, 40, 140, fill=journal.GOLD, width=9)

        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True); buf.seek(0)
        return buf


async def setup(bot):
    await bot.add_cog(Marriage(bot))
