"""Duel view — албал, устит, эрстинэ."""

from __future__ import annotations

import logging
from typing import Any

import discord

from core.exceptions import AetherError, GameStateError, ValidationError

log = logging.getLogger(__name__)
from services.games.duel_service import DuelService, DuelState
from ui.common.base import AetherView, refresh_panel, respond_error
from ui.embeds import duel_embed


class DuelView(AetherView):
    def __init__(
        self,
        duel: DuelState,
        duel_service: DuelService,
        challenger_name: str,
        opponent_name: str,
    ) -> None:
        super().__init__(
            duel.challenger_id, allowed_ids={duel.opponent_id}, timeout=600.0
        )
        self.duel = duel
        self.service = duel_service
        self.challenger_name = challenger_name
        self.opponent_name = opponent_name

    async def _update_panel(self, interaction: discord.Interaction) -> None:
        self._sync()
        await refresh_panel(
            interaction,
            embed=duel_embed(self.duel, self.challenger_name, self.opponent_name),
            view=self,
        )

    def _sync(self) -> None:
        self.accept_button.disabled = self.duel.status != "pending"
        self.decline_button.disabled = self.duel.status != "pending"
        active = self.duel.status == "active"
        self.attack_button.disabled = not active
        self.skill_button.disabled = not active
        self.defend_button.disabled = not active

    async def accept(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.duel.opponent_id:
            await respond_error(
                interaction,
                ValidationError("✦ Зөвхөн уригдсан тоглогч хүлээн авна."),
            )
            return
        try:
            self.duel = await self.service.accept(
                self.duel.duel_id, interaction.user.id
            )
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await self._update_panel(interaction)

    async def decline(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.duel.opponent_id:
            await respond_error(
                interaction,
                ValidationError("✦ Зөвхөн уригдсан тоглогч татгалзана."),
            )
            return
        try:
            self.duel = await self.service.decline(
                self.duel.duel_id, interaction.user.id
            )
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await self._update_panel(interaction)

    async def _attack(self, interaction: discord.Interaction, move: str) -> None:
        if interaction.user.id != self.duel.turn_id:
            await respond_error(interaction, GameStateError("✦ Одоо таны ээлж биш."))
            return
        try:
            self.duel = await self.service.attack(
                self.duel.duel_id, interaction.user.id, move
            )
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await self._update_panel(interaction)

    @discord.ui.button(
        label="✅ Хүлээн авах",
        style=discord.ButtonStyle.success,
        custom_id="duel_accept",
    )
    async def accept_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self.accept(interaction)

    @discord.ui.button(
        label="✖️ Татгалзах",
        style=discord.ButtonStyle.danger,
        custom_id="duel_decline",
    )
    async def decline_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self.decline(interaction)

    @discord.ui.button(
        label="💥 Довтлох",
        style=discord.ButtonStyle.primary,
        custom_id="duel_attack",
        row=1,
    )
    async def attack_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._attack(interaction, "attack")

    @discord.ui.button(
        label="💥 Critical Strike",
        style=discord.ButtonStyle.success,
        custom_id="duel_skill",
        row=1,
    )
    async def skill_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._attack(interaction, "skill")

    @discord.ui.button(
        label="🛡️ Хамгаалах",
        style=discord.ButtonStyle.secondary,
        custom_id="duel_defend",
        row=1,
    )
    async def defend_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._attack(interaction, "defend")

    async def on_timeout(self) -> None:
        if self.duel.status == "active":
            try:
                duel = await self.service.cancel(
                    self.duel.duel_id, self.duel.challenger_id
                )
                self.duel = duel
            except Exception as exc:
                log.debug("Duel timeout бүтэхгүй", exc_info=exc)
        await super().on_timeout()
