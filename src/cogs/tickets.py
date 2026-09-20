"""Private support tickets: panel, claim, close, and staff KPI integration."""
from __future__ import annotations

import time
import io
from typing import Optional

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.utils.embeds import accent_embed, error_embed, success_embed


TICKET_TYPES = {
    "discord": ("🔗", "Discord холболт", "Discord account, link, role асуудал"),
    "rules": ("📜", "Дүрэм", "Дүрэм, ban, warning асуулт"),
    "report": ("🚨", "Гомдол гаргах", "Нууц гомдол, report"),
    "cache": ("📥", "Татах / Cache алдаа", "Техник, cache, download алдаа"),
}


class TicketTypeSelect(ui.Select):
    def __init__(self, cog):
        super().__init__(placeholder="Ticket-ийн төрлөө сонгоно уу...", custom_id="aether_ticket_type_select", row=0,
                         options=[discord.SelectOption(label=label, value=key, emoji=emoji, description=description)
                                  for key, (emoji, label, description) in TICKET_TYPES.items()])
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.open_ticket(interaction, self.values[0])


class TicketPanel(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog
        self.add_item(TicketTypeSelect(cog))
        for key, (emoji, label, _) in TICKET_TYPES.items():
            button = ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary,
                               custom_id=f"aether_ticket_faq_{key}", row=1)
            button.callback = self._faq_callback(key)
            self.add_item(button)

    def _faq_callback(self, ticket_type):
        async def callback(interaction: discord.Interaction):
            text = TICKET_TYPES[ticket_type][2]
            await interaction.response.send_message(embed=accent_embed(f"{TICKET_TYPES[ticket_type][0]} {TICKET_TYPES[ticket_type][1]}", text), ephemeral=True)
        return callback


class TicketControls(ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(label="🙋 Claim", style=discord.ButtonStyle.success, custom_id="aether_ticket_claim")
    async def claim_ticket(self, interaction: discord.Interaction, _: ui.Button):
        await self.cog.claim_ticket(interaction)

    @ui.button(label="🔒 Close", style=discord.ButtonStyle.danger, custom_id="aether_ticket_close")
    async def close_ticket(self, interaction: discord.Interaction, _: ui.Button):
        await self.cog.close_ticket(interaction)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(TicketPanel(self))
        self.bot.add_view(TicketControls(self))

    async def _config(self, guild_id: int):
        return await self.bot.db_manager.fetch_one("ticket_config", {"guild_id": str(guild_id)})

    def _is_staff(self, member: discord.Member, config) -> bool:
        role_id = config.get("staff_role_id") if config else None
        return member.guild_permissions.manage_channels or bool(role_id and member.get_role(int(role_id)))

    @staticmethod
    def panel_embed():
        embed = discord.Embed(title="✦ AETHER — Тусламжийн төв", color=0xFF4FA3,
            description="Асуудал, асуулт байвал доороос төрлөө сонгож ticket нээнэ үү. Staff аль болох хурдан хариулна.\n\nХэрэв хүн шаардлагатай бол ticket дотор **Staff** дуудаж болно.\n\n**Түгээмэл асуултад** доорх товчоор шуурхай хариу аваарай.")
        embed.set_footer(text="AETHER SUPPORT • Төрлөө сонгоод эхлээрэй")
        return embed

    @app_commands.command(name="ticket_setup", description="Ticket panel болон staff тохируулах")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel,
                           staff_role: Optional[discord.Role] = None,
                           category: Optional[discord.CategoryChannel] = None,
                           log_channel: Optional[discord.TextChannel] = None):
        config = {"guild_id": str(interaction.guild_id), "category_id": category.id if category else None,
                  "staff_role_id": staff_role.id if staff_role else None, "panel_channel_id": channel.id,
                  "log_channel_id": log_channel.id if log_channel else None,
                  "updated_at": int(time.time())}
        await self.bot.db_manager.upsert("ticket_config", config, on_conflict="guild_id")
        message = await channel.send(embed=self.panel_embed(), view=TicketPanel(self))
        await self.bot.db_manager.update("ticket_config", {"guild_id": str(interaction.guild_id)}, {"panel_message_id": message.id})
        await interaction.response.send_message(
            f"✅ Ticket panel бэлэн боллоо. Transcript log: {log_channel.mention if log_channel else 'тохируулаагүй'}",
            ephemeral=True,
        )

    async def open_ticket(self, interaction: discord.Interaction, ticket_type: str = "discord"):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ticket-ийг зөвхөн сервер дотор нээнэ.", ephemeral=True)
        cfg = await self._config(interaction.guild.id)
        if not cfg:
            return await interaction.response.send_message("❌ Ticket system тохируулагдаагүй байна.", ephemeral=True)
        existing = await self.bot.db_manager.fetch_one("tickets", {"guild_id": str(interaction.guild.id), "opener_id": str(interaction.user.id), "status": "open"})
        if existing:
            return await interaction.response.send_message(f"🎫 Таны нээлттэй ticket: <#{existing['channel_id']}>", ephemeral=True)
        category = interaction.guild.get_channel(int(cfg["category_id"])) if cfg.get("category_id") else None
        overwrites = {interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                      interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
                      interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)}
        if cfg.get("staff_role_id") and (role := interaction.guild.get_role(int(cfg["staff_role_id"]))):
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        label = TICKET_TYPES.get(ticket_type, ("🎫", "support", ""))[1].lower().replace(" ", "-")
        channel = await interaction.guild.create_text_channel(f"ticket-{label}-{interaction.user.name}"[:90], category=category, overwrites=overwrites, reason="Aether ticket opened")
        await self.bot.db_manager.insert("tickets", {"guild_id": str(interaction.guild.id), "channel_id": channel.id, "opener_id": str(interaction.user.id), "subject": ticket_type, "status": "open", "created_at": int(time.time())})
        title = TICKET_TYPES.get(ticket_type, ("🎫", "Support", ""))
        await channel.send(embed=accent_embed(f"{title[0]} {title[1]} хүсэлт", f"{interaction.user.mention}, асуудлаа дэлгэрэнгүй бичнэ үү. Staff удахгүй хариулна."), view=TicketControls(self))
        await interaction.response.send_message(f"🎫 Ticket нээгдлээ: {channel.mention}", ephemeral=True)

    async def _ticket(self, channel_id: int):
        return await self.bot.db_manager.fetch_one("tickets", {"channel_id": channel_id, "status": "open"})

    async def claim_ticket(self, interaction: discord.Interaction):
        ticket, cfg = await self._ticket(interaction.channel_id), await self._config(interaction.guild_id)
        if not ticket or not self._is_staff(interaction.user, cfg):
            return await interaction.response.send_message("⛔ Энэ ticket-ийг claim хийх эрхгүй.", ephemeral=True)
        await self.bot.db_manager.update("tickets", {"id": ticket["id"]}, {"claimed_by": str(interaction.user.id)})
        await interaction.response.send_message(embed=success_embed("Ticket claimed", f"{interaction.user.mention} энэ ticket-ийг хариуцлаа."))

    async def close_ticket(self, interaction: discord.Interaction):
        ticket, cfg = await self._ticket(interaction.channel_id), await self._config(interaction.guild_id)
        if not ticket:
            return await interaction.response.send_message("❌ Нээлттэй ticket олдсонгүй.", ephemeral=True)
        if str(interaction.user.id) != str(ticket["opener_id"]) and not self._is_staff(interaction.user, cfg):
            return await interaction.response.send_message("⛔ Энэ ticket-ийг хаах эрхгүй.", ephemeral=True)
        transcript_lines = []
        async for message in interaction.channel.history(limit=1000, oldest_first=True):
            stamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            body = message.clean_content or "[embed/file]"
            transcript_lines.append(f"[{stamp}] {message.author} ({message.author.id}): {body}")
            for attachment in message.attachments:
                transcript_lines.append(f"  attachment: {attachment.url}")
        await self.bot.db_manager.update("tickets", {"id": ticket["id"]}, {"status": "closed", "closed_at": int(time.time()), "closed_by": str(interaction.user.id)})
        if self._is_staff(interaction.user, cfg):
            moderation = self.bot.get_cog("Moderation")
            if moderation:
                await moderation.add_ticket_closed(interaction.user.id, interaction.guild_id)
        await interaction.response.send_message(embed=success_embed("Ticket closed", "Ticket хаагдлаа. Энэ суваг удахгүй архивлагдана."))
        log_channel_id = cfg.get("log_channel_id") if cfg else None
        log_channel = interaction.guild.get_channel(int(log_channel_id)) if log_channel_id else None
        if isinstance(log_channel, discord.TextChannel):
            content = "\n".join(transcript_lines) or "No messages"
            file = discord.File(io.BytesIO(content.encode("utf-8")), filename=f"ticket-{ticket['id']}-transcript.txt")
            log_embed = accent_embed(
                "🎫 Ticket transcript",
                f"**Ticket:** #{ticket['id']}\n**Төрөл:** {ticket.get('subject') or 'support'}\n"
                f"**Нээсэн:** <@{ticket['opener_id']}>\n**Хаасан:** {interaction.user.mention}\n**Суваг:** {interaction.channel.name}",
            )
            await log_channel.send(embed=log_embed, file=file)
        await interaction.channel.edit(name=f"closed-{interaction.channel.name}"[:100], reason="Aether ticket closed")

    @app_commands.command(name="ticket_stats", description="Ticket системийн товч статистик")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        rows = await self.bot.db_manager.fetch_all("tickets", {"guild_id": str(interaction.guild_id)})
        opened = sum(1 for r in rows if r.get("status") == "open")
        closed = len(rows) - opened
        await interaction.response.send_message(embed=accent_embed("🎫 Ticket Statistics", f"**Нээлттэй:** {opened}\n**Хаагдсан:** {closed}\n**Нийт:** {len(rows)}"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
