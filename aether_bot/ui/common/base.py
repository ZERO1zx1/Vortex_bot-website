"""Aether-ийн нийтлэг View болон interaction туслахууд.

`AetherView` нь:
- зөвхөн зөвшөөрөгдсөн хэрэглэгчид товчлуурыг ажиллуулна,
- timeout болоход бүх товчлуурыг идэвхгүй болгож, мессежийг шинэчилнэ.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import discord

from core.exceptions import AetherError

log = logging.getLogger(__name__)

PERMISSION_MESSAGE = "✦ Энэ цэс зөвхөн эзэндээ нээлттэй."


class AetherView(discord.ui.View):
    """Author-only interactive view, timeout дээр auto-disable."""

    def __init__(
        self,
        author_id: int,
        *,
        allowed_ids: Iterable[int] | None = None,
        allow_all: bool = False,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.allow_all = allow_all
        self.allowed_ids: set[int] = {author_id, *(allowed_ids or ())}
        self.message: discord.Message | None = None

    def is_allowed(self, user_id: int) -> bool:
        return self.allow_all or user_id in self.allowed_ids

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.is_allowed(interaction.user.id):
            return True
        try:
            await interaction.response.send_message(PERMISSION_MESSAGE, ephemeral=True)
        except discord.HTTPException:
            log.debug("Permission хариу илгээж чадсангүй", exc_info=True)
        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True  # type: ignore[attr-defined]
        if self.message is None:
            return
        try:
            await self.message.edit(view=self)
        except discord.HTTPException:
            log.debug("Timeout view-ийг шинэчилж чадсангүй", exc_info=True)


async def refresh_panel(
    interaction: discord.Interaction,
    *,
    embed: discord.Embed,
    view: discord.ui.View,
) -> None:
    """Анхны мессежийг шинэчилж, боломжгүй бол шинэ мессеж илгээнэ."""
    try:
        if interaction.response.is_done():
            if interaction.message is not None:
                await interaction.message.edit(embed=embed, view=view)
            else:
                await interaction.followup.send(embed=embed, view=view)
        elif interaction.message is not None:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)
    except discord.HTTPException:
        log.debug("Панелийг шинэчилж чадсангүй", exc_info=True)


async def respond_error(interaction: discord.Interaction, error: Any) -> None:
    """Домайн алдааг хэрэглэгчид ойлгомжтой мессежээр харуулна."""
    message = (
        error.user_message
        if isinstance(error, AetherError)
        else "✦ Ямар нэгэн алдаа гарлаа. Дараа дахин оролдоно уу."
    )
    if not isinstance(error, AetherError):
        log.exception("UI interaction алдаа", exc_info=error)
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        log.debug("Алдааны хариу илгээж чадсангүй", exc_info=True)


def disable_all(view: discord.ui.View) -> None:
    for child in view.children:
        child.disabled = True  # type: ignore[attr-defined]
