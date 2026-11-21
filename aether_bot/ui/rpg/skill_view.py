"""Skill tree view — StringSelect + Upgrade / Activate."""

from __future__ import annotations

from typing import Any

import discord

from core.skill_catalog import ACTIVE, PATHS
from services.rpg.skill_service import SkillService, SkillTree
from ui.common.base import AetherView, refresh_panel
from ui.embeds import base_embed, skills_embed


class SkillTreeView(AetherView):
    def __init__(
        self,
        author_id: int,
        tree: SkillTree,
        skills: SkillService,
    ) -> None:
        super().__init__(author_id, timeout=300.0)
        self.tree = tree
        self.skills = skills
        self.selected: str | None = None
        self.skill_select: discord.ui.Select[Any] = discord.ui.Select(
            placeholder="🌌 Skill сонгох...",
            options=self._options(),
            custom_id="skill_select",
        )
        self.skill_select.callback = self._select_skill  # type: ignore[method-assign]
        self.add_item(self.skill_select)
        self._sync_buttons()

    def _options(self) -> list[discord.SelectOption]:
        options: list[discord.SelectOption] = []
        for path_id, states in self.tree.paths.items():
            path = PATHS.get(path_id)
            path_name = path.name if path else path_id.title()
            for state in states:
                skill = state.skill
                options.append(
                    discord.SelectOption(
                        label=f"{skill.icon} {skill.name}"[:100],
                        value=skill.skill_id,
                        description=(
                            f"{path_name} · Lv.{state.level}/{skill.max_level} · "
                            f"{'Active' if skill.kind == ACTIVE else 'Passive'}"
                        )[:100],
                        default=skill.skill_id == self.selected,
                    )
                )
        return options[:25]

    def _state(self) -> Any:
        if self.selected is None:
            return None
        for states in self.tree.paths.values():
            for state in states:
                if state.skill.skill_id == self.selected:
                    return state
        return None

    def _sync_buttons(self) -> None:
        state = self._state()
        can_upgrade = (
            state is not None
            and self.tree.skill_points > 0
            and state.level < state.skill.max_level
            and self.tree.level >= state.skill.unlock_level
        )
        can_activate = (
            state is not None
            and state.skill.kind == ACTIVE
            and state.level > 0
            and not state.is_active
            and state.cooldown_remaining <= 0
        )
        self.upgrade_button.disabled = not can_upgrade
        self.activate_button.disabled = not can_activate

    def _rebuild(self) -> None:
        self.skill_select.options = self._options()
        self._sync_buttons()

    async def _select_skill(self, interaction: discord.Interaction) -> None:
        self.selected = self.skill_select.values[0]
        self._rebuild()
        await interaction.response.edit_message(
            embed=skills_embed(self.tree), view=self
        )

    @discord.ui.button(
        label="➕ +1 Сайжруулах",
        style=discord.ButtonStyle.success,
        custom_id="skill_upgrade",
        disabled=True,
    )
    async def upgrade_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        if self.selected is None:
            return
        result = await self.skills.upgrade(interaction.user.id, self.selected)
        self.tree = await self.skills.get_tree(interaction.user.id)
        self._rebuild()
        embed = skills_embed(self.tree)
        embed.add_field(
            name="✅ Сайжирлаа",
            value=f"**{result.skill.name}** Lv.{result.previous_level} → "
            f"**Lv.{result.new_level}** · {result.skill_points_left} SP үлдсэн",
            inline=False,
        )
        await refresh_panel(interaction, embed=embed, view=self)

    @discord.ui.button(
        label="✨ Идэвхжүүлэх",
        style=discord.ButtonStyle.primary,
        custom_id="skill_activate",
        disabled=True,
    )
    async def activate_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        if self.selected is None:
            return
        result = await self.skills.activate(interaction.user.id, self.selected)
        self.tree = await self.skills.get_tree(interaction.user.id)
        self._rebuild()
        embed = base_embed(
            f"✨ {result.skill.icon} {result.skill.name}",
            f"Идэвхтэй · <t:{int(result.active_until.timestamp())}:R> хүртэл\n"
            f"Cooldown: `{result.cooldown_sec // 60}м`",
            color=0x00E5FF,
        )
        await refresh_panel(interaction, embed=embed, view=self)
