"""Balance view — Wallet/Bank үйлдлүүд Modal-аар."""

from __future__ import annotations

from typing import Any

import discord

import config
from services.economy.wallet_service import WalletService
from services.rpg.skill_service import SkillService
from ui.common.base import AetherView, refresh_panel
from ui.common.modals import AmountModal, TransferModal
from ui.embeds import balance_embed, base_embed, format_number


class BalanceView(AetherView):
    def __init__(
        self,
        author_id: int,
        wallet: WalletService,
        skills: SkillService,
        display_name: str,
    ) -> None:
        super().__init__(author_id)
        self.wallet = wallet
        self.skills = skills
        self.display_name = display_name

    async def _render(self, interaction: discord.Interaction) -> None:
        user = await self.wallet.balance(interaction.user.id)
        mods = await self.skills.get_modifiers(interaction.user.id)
        await refresh_panel(
            interaction,
            embed=balance_embed(user, mods, self.display_name),
            view=self,
        )

    @discord.ui.button(
        label="📥 Хийх", style=discord.ButtonStyle.success, custom_id="balance_dep"
    )
    async def deposit(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            result = await self.wallet.deposit(it.user.id, value)
            embed = base_embed(
                "📥 Aether Deposit",
                f"**{format_number(result.amount)}** ⛃ банкинд шилжлээ.",
                color=config.SUCCESS,
            )
            embed.add_field(
                name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃"
            )
            embed.add_field(name="🏦 Bank", value=f"**{format_number(result.bank)}** ⛃")
            await refresh_panel(it, embed=embed, view=self)

        await interaction.response.send_modal(
            AmountModal(
                title="📥 Aether Deposit",
                label="Хийх дүн",
                callback=submit,
            )
        )

    @discord.ui.button(
        label="📤 Авах", style=discord.ButtonStyle.primary, custom_id="balance_wd"
    )
    async def withdraw(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(it: discord.Interaction, value: str) -> None:
            result = await self.wallet.withdraw(it.user.id, value)
            embed = base_embed(
                "📤 Aether Withdraw",
                f"**{format_number(result.amount)}** ⛃ Wallet руу буцлаа.",
                color=config.CYAN,
            )
            embed.add_field(
                name="👛 Wallet", value=f"**{format_number(result.wallet)}** ⛃"
            )
            embed.add_field(name="🏦 Bank", value=f"**{format_number(result.bank)}** ⛃")
            await refresh_panel(it, embed=embed, view=self)

        await interaction.response.send_modal(
            AmountModal(
                title="📤 Aether Withdraw",
                label="Авах дүн",
                callback=submit,
            )
        )

    @discord.ui.button(
        label="💸 Шилжүүлэх",
        style=discord.ButtonStyle.secondary,
        custom_id="balance_pay",
    )
    async def transfer(
        self, interaction: discord.Interaction, button: discord.ui.Button[Any]
    ) -> None:
        async def submit(
            it: discord.Interaction, recipient_id: int, value: str
        ) -> None:
            result = await self.wallet.transfer(it.user.id, recipient_id, value)
            embed = base_embed(
                "💸 Aether Transfer",
                f"<@{recipient_id}> руу **{format_number(result.net)}** ⛃ илгээгдлээ.",
                color=config.SUCCESS,
            )
            if result.tax:
                embed.add_field(
                    name="🏛️ Tax", value=f"**{format_number(result.tax)}** ⛃"
                )
            embed.add_field(
                name="👛 Wallet",
                value=f"**{format_number(result.sender_wallet)}** ⛃",
            )
            await refresh_panel(it, embed=embed, view=self)

        await interaction.response.send_modal(TransferModal(callback=submit))
