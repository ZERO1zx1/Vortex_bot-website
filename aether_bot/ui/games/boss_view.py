"""Boss view — World Boss: сонгох + Атак / Critical Strike."""

from __future__ import annotations

from typing import Any

import discord

from core.exceptions import AetherError
from services.games.boss_service import BossService
from ui.common.base import AetherView, refresh_panel, respond_error
from ui.embeds import boss_attack_embed, boss_status_embed


class BossView(AetherView):
    def __init__(
        self,
        boss_ids: list[str],
        service: BossService,
        display_name: str,
    ) -> None:
        super().__init__(0, allow_all=True, timeout=600.0)
        self.boss_ids = boss_ids
        self.service = service
        self.display_name = display_name
        self.selected: str | None = boss_ids[0] if boss_ids else None
        self._sync()
        options = [
            discord.SelectOption(
                label=f"{boss.icon} {boss.name}"[:100],
                value=boss.boss_id,
                description=f"HP {boss.hp:,} · +{boss.coin_reward:,} ⛃"[:100],
            )
            for boss in BossView.available_bosses()
        ]
        if options:
            self.select: discord.ui.Select[Any] = discord.ui.Select(
                placeholder="👹 Boss сонгох...",
                options=options,
                custom_id="boss_select",
            )
            self.select.callback = self._select  # type: ignore[method-assign]
            self.add_item(self.select)

    @classmethod
    def available_bosses(cls) -> list[Any]:
        from services.games.boss_service import load_bosses

        return load_bosses()

    def _sync(self) -> None:
        self.attack_button.disabled = self.selected is None
        self.skill_button.disabled = self.selected is None

    async def _select(self, interaction: discord.Interaction) -> None:
        self.selected = self.select.values[0]
        self._sync()
        status = await self.service.status(self.selected)
        await refresh_panel(interaction, embed=boss_status_embed(status), view=self)

    async def _attack(
        self, interaction: discord.Interaction, *, use_skill: bool
    ) -> None:
        if self.selected is None:
            await interaction.response.send_message("✦ Boss сонгохгүй байна.")
            return
        try:
            attack = await self.service.attack(
                interaction.user.id, self.selected, use_skill=use_skill
            )
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await refresh_panel(
            interaction,
            embed=boss_attack_embed(attack, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="⚔️ Атак",
        style=discord.ButtonStyle.primary,
        custom_id="boss_attack",
    )
    async def attack_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._attack(interaction, use_skill=False)

    @discord.ui.button(
        label="💥 Critical Strike",
        style=discord.ButtonStyle.success,
        custom_id="boss_crit",
    )
    async def skill_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        await self._attack(interaction, use_skill=True)
