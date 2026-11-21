"""Admin cog — slash-only `/admin_*` командууд."""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from cogs._bot_types import AetherBotProtocol
from core.checks import is_admin
from core.exceptions import AetherError
from ui.common.base import respond_error
from ui.embeds import base_embed

log = logging.getLogger(__name__)


def _embed(title: str, lines: list[tuple[str, str]]) -> discord.Embed:
    embed = base_embed(title, color=0x5865F2)
    for name, value in lines:
        embed.add_field(name=name, value=value, inline=False)
    return embed


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: AetherBotProtocol = bot  # type: ignore[assignment]

    @app_commands.command(name="admin_economy")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def admin_economy(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action: str,
        amount: int,
    ) -> None:
        try:
            user = await self.bot.wallet.balance(member.id)
            if action == "grant":
                wallet = await self.bot.wallet.credit(member.id, amount, "admin_grant")
                lines = [
                    ("🧾 Action", "admin_grant"),
                    ("🧑 Target", f"<@{member.id}>"),
                    ("🪙 Amount", f"**{amount:,}** ⛃"),
                    ("👛 Wallet", f"**{wallet:,}** ⛃"),
                ]
            elif action == "remove":
                wallet = await self.bot.wallet.spend(member.id, amount, "admin_remove")
                lines = [
                    ("🧾 Action", "admin_remove"),
                    ("🧑 Target", f"<@{member.id}>"),
                    ("🪙 Amount", f"**{amount:,}** ⛃"),
                    ("👛 Wallet", f"**{wallet:,}** ⛃"),
                ]
            elif action == "balance":
                lines = [
                    ("🧑 Target", f"<@{member.id}>"),
                    ("👛 Wallet", f"**{user.wallet:,}** ⛃"),
                    ("🏦 Bank", f"**{user.bank:,}** ⛃"),
                ]
            else:
                raise ValueError("action should be grant/remove/balance")
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        except ValueError as exc:
            await respond_error(interaction, AetherError(f"✦ {exc}."))
            return
        await interaction.response.send_message(
            "✦ **Aether Admin: Economy**",
            embed=_embed("✦ Admin Economy", lines),
            ephemeral=True,
        )

    @app_commands.command(name="admin_jail")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def admin_jail(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action: str,
        minutes: int | None = None,
        bail: int | None = None,
        reason: str = "admin",
    ) -> None:
        try:
            status = await self.bot.jail.status(member.id)
            if action == "imprison":
                result = await self.bot.jail.imprison(
                    member.id,
                    minutes=minutes or 10,
                    bail_cost=bail or 1000,
                    reason=reason,
                )
                lines = [
                    ("👥 Member", f"<@{member.id}>"),
                    ("⏳ Minutes", str(result.minutes)),
                    ("💰 Bail", f"**{result.bail_cost:,}** ⛃"),
                ]
            elif action == "release":
                await self.bot.jail.release(member.id, reason="admin")
                status = await self.bot.jail.status(member.id)
                lines = [
                    ("👥 Member", f"<@{member.id}>"),
                    ("🕊️ Status", "Released by admin."),
                ]
            elif action == "status":
                lines = [
                    ("👥 Member", f"<@{member.id}>"),
                    ("⛓️ Jailed", "Yes" if status.jailed else "No"),
                    ("💰 Bail", f"**{status.bail_cost:,}** ⛃"),
                ]
            else:
                raise ValueError("action should be imprison/release/status")
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        except ValueError as exc:
            await respond_error(interaction, AetherError(f"✦ {exc}."))
            return
        await interaction.response.send_message(
            embed=_embed("✦ Admin Jail", lines), ephemeral=True
        )

    @app_commands.command(name="admin_shop")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def admin_shop(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        item_id: str,
        quantity: int = 1,
    ) -> None:
        try:
            await self.bot.shop.grant_item(member.id, item_id, quantity)
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        await interaction.response.send_message(
            embed=_embed(
                "✦ Admin Shop",
                [
                    ("👥 Member", f"<@{member.id}>"),
                    ("🎁 Item", f"`{item_id}`"),
                    ("📦 Quantity", str(quantity)),
                ],
            ),
            ephemeral=True,
        )

    @app_commands.command(name="admin_skill")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def admin_skill(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        action: str,
        skill_id: str,
        amount: int = 1,
    ) -> None:
        try:
            if action == "grant_sp":
                sp = await self.bot.user_repo.grant_skill_points(member.id, amount)
                lines = [
                    ("👥 Member", f"<@{member.id}>"),
                    ("✨ SP", f"+{amount} (total {sp})"),
                ]
            elif action == "reset":
                result = await self.bot.skills.reset(member.id)
                lines = [
                    ("👥 Member", f"<@{member.id}>"),
                    ("🔄 Reset", f"refunded {result.refunded_points} SP"),
                ]
            else:
                raise ValueError("action should be grant_sp/reset")
        except AetherError as exc:
            await respond_error(interaction, exc)
            return
        except ValueError as exc:
            await respond_error(interaction, AetherError(f"✦ {exc}."))
            return
        await interaction.response.send_message(
            embed=_embed("✦ Admin Skill", lines), ephemeral=True
        )

    @app_commands.command(name="admin_config")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @is_admin()
    async def admin_config(
        self,
        interaction: discord.Interaction,
        key: str,
        value: str,
    ) -> None:
        if interaction.guild is None:
            await respond_error(interaction, AetherError("✦ Guild контекст байхгүй."))
            return
        guild_id = interaction.guild.id
        key = key.lower()
        if key == "prefix":
            await self.bot.guild_repo.set_prefix(guild_id, value)
            lines = [("🧩 Prefix", f"`{value}`")]
        elif key == "tax":
            try:
                tax_pct = float(value.replace("%", "")) / 100.0
            except ValueError:
                await respond_error(
                    interaction, AetherError("✦ Tax дүнүүд 0–50% байна.")
                )
                return
            await self.bot.guild_repo.set_tax(guild_id, tax_pct)
            lines = [("🧾 Tax", f"**{tax_pct * 100:.1f}%**")]
        elif key == "log_channel":
            channel = (
                interaction.guild.get_channel(int(value)) if value.isdigit() else None
            )
            await self.bot.guild_repo.set_log_channel(
                guild_id, int(value) if value.isdigit() else None
            )
            lines = [
                (
                    "🪪 Log channel",
                    f"#{channel.name if channel else '—'}" if value.isdigit() else "—",
                )
            ]
        else:
            await respond_error(
                interaction,
                AetherError("✦ prefix/tax/log_channel хэрэгсэлгүй."),
            )
            return
        await interaction.response.send_message(
            embed=_embed("✦ Admin Config", lines), ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Admin(bot))
