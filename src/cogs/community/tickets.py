"""Private support tickets: panel, claim, close, and staff KPI integration."""
from __future__ import annotations

import asyncio
import io
import time
import weakref

import discord
from discord import app_commands, ui
from discord.ext import commands

from src.ui.setup import SetupPanel, SetupState, mention_or_missing
from src.utils.embeds import accent_embed, success_embed

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
        # Serialises ticket opening per (guild, user). The type select is a
        # persistent view, so a double-click (or two clients sending at once)
        # reached open_ticket concurrently; both passed the "already has an
        # open ticket" read and each created its own channel + row.
        # Weak values: the lock only has to outlive the critical section.
        self._open_locks: weakref.WeakValueDictionary[tuple[int, int], asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )

    def _open_lock(self, guild_id: int, user_id: int) -> asyncio.Lock:
        key = (int(guild_id), int(user_id))
        lock = self._open_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._open_locks[key] = lock
        return lock

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
        embed = discord.Embed(
            title="✦ AETHER тусламжийн төв",
            description="Асуудлын төрлөө сонгоход зөвхөн танд болон staff-д харагдах суваг нээгдэнэ.",
            color=0xFF4FA3,
        )
        embed.add_field(
            name="🎫 Ticket нээх",
            value="Дээд талын цэснээс асуудлын төрлөө сонгоно.",
            inline=False,
        )
        embed.add_field(
            name="⚡ Шуурхай хариулт",
            value="Түгээмэл асуултын товчийг дарвал хариулт зөвхөн танд харагдана.",
            inline=False,
        )
        embed.add_field(
            name="🔐 Нууцлал",
            value="Ticket сувагт та болон эрхтэй staff л нэвтэрнэ.",
            inline=False,
        )
        embed.set_footer(text="Төрлөө сонгоод эхлээрэй • AETHER SUPPORT")
        return embed

    @app_commands.command(name="ticket_setup", description="Ticket panel болон staff тохируулах")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setup_ticket(self, interaction: discord.Interaction, channel: discord.TextChannel,
                           staff_role: discord.Role | None = None,
                           category: discord.CategoryChannel | None = None,
                           log_channel: discord.TextChannel | None = None):
        permissions = channel.permissions_for(interaction.guild.me)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
            return await interaction.response.send_message(
                "❌ Ботод сонгосон сувагт `View Channel`, `Send Messages`, `Embed Links` эрх хэрэгтэй.",
                ephemeral=True,
            )
        await interaction.response.defer(ephemeral=True)
        config = {"guild_id": str(interaction.guild_id), "category_id": category.id if category else None,
                  "staff_role_id": staff_role.id if staff_role else None, "panel_channel_id": channel.id,
                  "log_channel_id": log_channel.id if log_channel else None,
                  "updated_at": int(time.time())}
        await self.bot.db_manager.upsert("ticket_config", config, on_conflict="guild_id")
        message = await channel.send(embed=self.panel_embed(), view=TicketPanel(self))
        await self.bot.db_manager.update("ticket_config", {"guild_id": str(interaction.guild_id)}, {"panel_message_id": message.id})
        result = (
            SetupPanel(
                "Ticket систем",
                "Олон нийтэд харагдах ticket panel амжилттай байршууллаа.",
                icon="🎫",
                state=SetupState.READY,
            )
            .section("Тохиргоо", [
                f"📍 Panel суваг  {channel.mention}",
                f"🗂️ Ticket ангилал  {mention_or_missing(category, missing='Автоматаар үүсгэнэ')}",
                f"🛡️ Staff роль  {mention_or_missing(staff_role, missing='Manage Channels эрх ашиглана')}",
                f"📝 Transcript лог  {mention_or_missing(log_channel)}",
            ], icon="⚙️")
            .finish("Panel message ID хадгалагдсан")
        )
        await interaction.followup.send(embed=result, ephemeral=True)

    async def open_ticket(self, interaction: discord.Interaction, ticket_type: str = "discord"):
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("❌ Ticket-ийг зөвхөн сервер дотор нээнэ.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        # The duplicate check, the channel creation and the row insert all run
        # under one lock: reading "no open ticket" and then inserting is a
        # read-modify-write that a second click can duplicate.
        async with self._open_lock(interaction.guild.id, interaction.user.id):
            cfg = await self._config(interaction.guild.id)
            if not cfg:
                return await interaction.followup.send("❌ Ticket system тохируулагдаагүй байна.", ephemeral=True)
            existing = await self.bot.db_manager.fetch_one("tickets", {"guild_id": str(interaction.guild.id), "opener_id": str(interaction.user.id), "status": "open"})
            if existing:
                return await interaction.followup.send(f"🎫 Таны нээлттэй ticket: <#{existing['channel_id']}>", ephemeral=True)
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
            await interaction.followup.send(f"🎫 Ticket нээгдлээ: {channel.mention}", ephemeral=True)

    async def _ticket(self, channel_id: int):
        return await self.bot.db_manager.fetch_one("tickets", {"channel_id": channel_id, "status": "open"})

    async def claim_ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ticket, cfg = await self._ticket(interaction.channel_id), await self._config(interaction.guild_id)
        if not ticket or not self._is_staff(interaction.user, cfg):
            return await interaction.followup.send("⛔ Энэ ticket-ийг claim хийх эрхгүй.", ephemeral=True)
        existing = ticket.get("claimed_by")
        if existing is not None and str(existing) != str(interaction.user.id):
            return await interaction.followup.send(
                f"⛔ Энэ ticket-ийг <@{existing}> аль хэдийн claim хийсэн байна.", ephemeral=True,
            )
        # Compare-and-set in PostgreSQL, including the NULL case. This also
        # protects claims after a restart and across multiple bot workers.
        changed = await self.bot.db_manager.update(
            "tickets", {"id": ticket["id"], "status": "open", "claimed_by": existing},
            {"claimed_by": str(interaction.user.id)},
        )
        if not changed:
            return await interaction.followup.send(
                "⛔ Ticket-ийн төлөв өөрчлөгдсөн байна. Дахин шалгана уу.", ephemeral=True,
            )
        await interaction.followup.send(embed=success_embed("Ticket claimed", f"{interaction.user.mention} энэ ticket-ийг хариуцлаа."), ephemeral=True)

    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        ticket, cfg = await self._ticket(interaction.channel_id), await self._config(interaction.guild_id)
        if not ticket:
            return await interaction.followup.send("❌ Нээлттэй ticket олдсонгүй.", ephemeral=True)
        if str(interaction.user.id) != str(ticket["opener_id"]) and not self._is_staff(interaction.user, cfg):
            return await interaction.followup.send("⛔ Энэ ticket-ийг хаах эрхгүй.", ephemeral=True)
        transcript_lines = []
        async for message in interaction.channel.history(limit=1000, oldest_first=True):
            stamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
            body = message.clean_content or "[embed/file]"
            transcript_lines.append(f"[{stamp}] {message.author} ({message.author.id}): {body}")
            for attachment in message.attachments:
                transcript_lines.append(f"  attachment: {attachment.url}")
        changed = await self.bot.db_manager.update("tickets", {"id": ticket["id"], "status": "open"}, {"status": "closed", "closed_at": int(time.time()), "closed_by": str(interaction.user.id)})
        if not changed:
            return await interaction.followup.send("🎫 Ticket аль хэдийн хаагдсан байна.", ephemeral=True)
        if self._is_staff(interaction.user, cfg):
            moderation = self.bot.get_cog("Moderation")
            if moderation:
                await moderation.add_ticket_closed(interaction.user.id, interaction.guild_id)
        await interaction.followup.send(embed=success_embed("Ticket closed", "Ticket хаагдлаа."), ephemeral=True)
        log_channel_id = cfg.get("log_channel_id") if cfg else None
        log_channel = interaction.guild.get_channel(int(log_channel_id)) if log_channel_id else None
        archived = False
        if isinstance(log_channel, discord.TextChannel):
            content = "\n".join(transcript_lines) or "No messages"
            file = discord.File(io.BytesIO(content.encode("utf-8")), filename=f"ticket-{ticket['id']}-transcript.txt")
            log_embed = accent_embed(
                "🎫 Ticket transcript",
                f"**Ticket:** #{ticket['id']}\n**Төрөл:** {ticket.get('subject') or 'support'}\n"
                f"**Нээсэн:** <@{ticket['opener_id']}>\n**Хаасан:** {interaction.user.mention}\n**Суваг:** {interaction.channel.name}",
            )
            await log_channel.send(embed=log_embed, file=file)
            archived = True
        # The channel used to be renamed and left in place forever, so a busy
        # guild accumulated one channel per ticket with nothing ever
        # reclaiming it. Now it is removed -- but only once the transcript has
        # actually been delivered, so closing a ticket without a configured
        # log channel never destroys the conversation.
        if archived:
            try:
                await interaction.channel.delete(reason="Aether ticket archived")
            except discord.Forbidden:
                await interaction.channel.edit(
                    name=f"closed-{interaction.channel.name}"[:100],
                    reason="Aether ticket closed",
                )
        else:
            await interaction.channel.edit(
                name=f"closed-{interaction.channel.name}"[:100],
                reason="Aether ticket closed",
            )

    @app_commands.command(name="ticket_stats", description="Ticket системийн товч статистик")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        rows = await self.bot.db_manager.fetch_all("tickets", {"guild_id": str(interaction.guild_id)})
        opened = sum(1 for r in rows if r.get("status") == "open")
        closed = len(rows) - opened
        await interaction.followup.send(embed=accent_embed("🎫 Ticket Statistics", f"**Нээлттэй:** {opened}\n**Хаагдсан:** {closed}\n**Нийт:** {len(rows)}"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Tickets(bot))
