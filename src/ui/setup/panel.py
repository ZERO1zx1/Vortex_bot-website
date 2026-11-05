"""Aether's visual and interaction contract for setup panels."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum

import discord

from src.utils.branding import BOT_NAME
from src.utils.constants import ERROR_COLOR, INFO_COLOR, SUCCESS_COLOR, WARNING_COLOR


class SetupState(StrEnum):
    READY = "ready"
    INCOMPLETE = "incomplete"
    DISABLED = "disabled"
    DRAFT = "draft"


_STATE_META = {
    SetupState.READY: ("✅", "Ажиллахад бэлэн", SUCCESS_COLOR),
    SetupState.INCOMPLETE: ("⚠️", "Тохиргоо дутуу", WARNING_COLOR),
    SetupState.DISABLED: ("⏸️", "Унтраалттай", ERROR_COLOR),
    SetupState.DRAFT: ("📝", "Бэлтгэж байна", INFO_COLOR),
}

ADMIN_CONSOLE_LABEL = "Aether Admin Console"
ADMIN_ACCESS_LABEL = "Удирдах эрх шаардлагатай"


class SetupPanel:
    """Build an Aether admin surface with status-first information hierarchy."""

    def __init__(
        self,
        title: str,
        description: str,
        *,
        icon: str,
        state: SetupState,
        status: str | None = None,
        color: int | None = None,
    ):
        marker, default_status, state_color = _STATE_META[state]
        self.embed = discord.Embed(
            title=f"{icon} {title}",
            description=(
                f"> {marker} **{status or default_status}**\n"
                f"> 🔐 {ADMIN_ACCESS_LABEL}\n\n"
                f"{description}"
            ),
            color=color if color is not None else state_color,
            timestamp=datetime.now(UTC),
        )
        self.embed.set_author(name=f"🛡️ {ADMIN_CONSOLE_LABEL}")

    def section(
        self,
        title: str,
        lines: Iterable[str],
        *,
        icon: str = "•",
        inline: bool = False,
    ) -> SetupPanel:
        content = "\n".join(str(line) for line in lines if line)
        self.embed.add_field(
            name=f"{icon} {title}",
            value=content or "—",
            inline=inline,
        )
        return self

    def finish(self, hint: str, *, actor=None) -> discord.Embed:
        owner = f"Нээсэн: {actor.display_name} • " if actor is not None else ""
        footer = {"text": f"🔐 {owner}{hint} • {BOT_NAME}"}
        avatar = getattr(getattr(actor, "display_avatar", None), "url", None)
        if avatar:
            footer["icon_url"] = avatar
        self.embed.set_footer(**footer)
        return self.embed


class ConfirmActionView(discord.ui.View):
    """Short-lived, actor-bound confirmation for destructive setup actions."""

    def __init__(self, author_id: int, guild_id: int, *, timeout: float = 30):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.guild_id = guild_id
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id != self.guild_id or interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "❌ Энэ баталгаажуулалт өөр админых байна.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Тийм, үргэлжлүүлэх", emoji="✓", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Болих", emoji="✕", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Үйлдлийг цуцаллаа.", view=self)
        self.stop()


def state_text(enabled: bool, *, enabled_label="Идэвхтэй", disabled_label="Унтраалттай") -> str:
    return f"{'✅' if enabled else '⏸️'} {enabled_label if enabled else disabled_label}"


def mention_or_missing(item, *, missing="Тохируулаагүй") -> str:
    return item.mention if item is not None else f"⚠️ {missing}"


def sync_toggle_button(
    button: discord.ui.Button,
    enabled: bool,
    *,
    disable_label: str,
    enable_label: str,
) -> None:
    """Make a toggle describe the action it will perform, not current state."""
    button.label = disable_label if enabled else enable_label
    button.style = discord.ButtonStyle.danger if enabled else discord.ButtonStyle.success


async def disable_setup_panel(view: discord.ui.View, message) -> None:
    for child in view.children:
        child.disabled = True
    if message is None:
        return
    try:
        await message.edit(view=view)
    except (discord.NotFound, discord.HTTPException):
        return
