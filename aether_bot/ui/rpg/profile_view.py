"""Profile view — Inventory / Skills / Bio."""

from __future__ import annotations

from typing import Any

import discord

from repositories.user_repo import UserRepository
from services.economy.wallet_service import WalletService
from services.rpg.inventory_service import InventoryService
from services.rpg.level_service import LevelService
from services.rpg.skill_service import SkillService
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import BioModal
from ui.embeds import profile_embed, skills_embed
from ui.rpg.inventory_view import InventoryView
from ui.rpg.skill_view import SkillTreeView


class ProfileView(AetherView):
    def __init__(
        self,
        author_id: int,
        display_name: str,
        users: UserRepository,
        wallet: WalletService,
        levels: LevelService,
        skills: SkillService,
        inventory: InventoryService,
    ) -> None:
        super().__init__(author_id)
        self.display_name = display_name
        self.users = users
        self.wallet = wallet
        self.levels = levels
        self.skills = skills
        self.inventory = inventory

    async def _embed(self, user_id: int) -> discord.Embed:
        user = await self.wallet.balance(user_id)
        mods = await self.skills.get_modifiers(user_id)
        progress = await self.levels.progress(user_id)
        return profile_embed(user, mods, progress, self.display_name)

    @discord.ui.button(
        label="🎒 Inventory",
        style=discord.ButtonStyle.primary,
        custom_id="profile_inventory",
    )
    async def inventory_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        embed, view = await InventoryView.create(
            interaction.user.id, self.inventory, self.display_name
        )
        await refresh_panel(interaction, embed=embed, view=view)

    @discord.ui.button(
        label="🌌 Skills",
        style=discord.ButtonStyle.success,
        custom_id="profile_skills",
    )
    async def skills_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        tree = await self.skills.get_tree(interaction.user.id)
        view = SkillTreeView(interaction.user.id, tree, self.skills)
        await refresh_panel(interaction, embed=skills_embed(tree), view=view)

    @discord.ui.button(
        label="📜 Bio",
        style=discord.ButtonStyle.secondary,
        custom_id="profile_bio",
    )
    async def bio_button(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        user = await self.wallet.balance(interaction.user.id)

        async def submit(it: discord.Interaction, value: str) -> None:
            await self.users.set_bio(
                it.user.id, value.strip() or "Aether ертөнцийн аялагч."
            )
            await refresh_panel(it, embed=await self._embed(it.user.id), view=self)

        await interaction.response.send_modal(
            BioModal(callback=submit, current=user.bio)
        )
