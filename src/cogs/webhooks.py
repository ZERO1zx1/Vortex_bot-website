"""Discord-native webhook automation with safe, per-server templates."""
from __future__ import annotations

import time

import discord
from discord import app_commands
from discord.ext import commands

from src.core.exceptions import DatabaseSchemaError
from src.utils.embeds import accent_embed, error_embed, success_embed


EVENTS = {
    "member_join": "Гишүүн орж ирэхэд",
    "member_leave": "Гишүүн гарахад",
}


class WebhookAutomation(commands.Cog):
    """Automation is intentionally Discord-native: no arbitrary outbound URLs."""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="automation_setup", description="Join/leave message тохируулах — /automation_help заавар")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(event=[
        app_commands.Choice(name="Гишүүн орж ирэхэд", value="member_join"),
        app_commands.Choice(name="Гишүүн гарахад", value="member_leave"),
    ])
    async def automation_setup(
        self,
        interaction: discord.Interaction,
        event: app_commands.Choice[str],
        channel: discord.TextChannel,
        message: str,
        log_channel: discord.TextChannel | None = None,
    ):
        message = message.strip()
        if not message or len(message) > 1800:
            return await interaction.response.send_message(
                "❌ Message 1–1800 тэмдэгт байх ёстой.", ephemeral=True
            )
        now = int(time.time())
        await self.bot.db_manager.upsert(
            "automation_rules",
            {
                "guild_id": str(interaction.guild_id), "event_name": event.value,
                "channel_id": channel.id, "log_channel_id": log_channel.id if log_channel else None, "message_template": message,
                "enabled": True, "created_by": str(interaction.user.id),
                "updated_at": now,
            },
            on_conflict="guild_id,event_name",
        )
        await interaction.response.send_message(
            embed=success_embed("✦ Automation ready", f"**{EVENTS[event.value]}** → {channel.mention}\nLog: {log_channel.mention if log_channel else 'тохируулаагүй'}\n`{{member}}`, `{{server}}`, `{{count}}` ашиглаж болно."),
            ephemeral=True,
        )

    @app_commands.command(name="automation_help", description="Automation setup хийх заавар")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automation_help(self, interaction: discord.Interaction):
        embed = accent_embed(
            "⚡ Automation хэрхэн тохируулах вэ?",
            "**1.** `/automation_setup` гэж бичнэ.\n"
            "**2.** `event` дээр member join эсвэл leave-ийг сонгоно.\n"
            "**3.** `channel` дээр автоматаар message орох сувгаа сонгоно.\n"
            "**4.** `message` дээр илгээх текстээ бичнэ.\n\n"
            "**Жишээ:** `🌸 {member}, {server}-д тавтай морил! Одоо бид {count} гишүүнтэй.`\n\n"
            "**Тусгай үгс:**\n`{member}` — хэрэглэгч\n`{server}` — серверийн нэр\n`{count}` — нийт гишүүд\n\n"
            "Тохируулгаа харах: `/automation_status`\nУнтраах: `/automation_disable`",
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="automation_test", description="Automation message-ийг шууд test хийх")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(event=[
        app_commands.Choice(name="Гишүүн орж ирэхэд", value="member_join"),
        app_commands.Choice(name="Гишүүн гарахад", value="member_leave"),
    ])
    async def automation_test(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        rule = await self.bot.db_manager.fetch_one("automation_rules", {"guild_id": str(interaction.guild_id), "event_name": event.value})
        if not rule:
            return await interaction.response.send_message("❌ Эхлээд `/automation_setup` хийж rule үүсгэнэ үү.", ephemeral=True)
        channel = interaction.guild.get_channel(int(rule["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message("❌ Тохируулсан суваг олдсонгүй.", ephemeral=True)
        message = (rule["message_template"].replace("{member}", interaction.user.mention)
                   .replace("{server}", interaction.guild.name)
                   .replace("{count}", str(interaction.guild.member_count or 0)))
        await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
        await interaction.response.send_message(f"✅ Test message {channel.mention} руу явлаа.", ephemeral=True)

    @app_commands.command(name="automation_embed", description="Automation message-ийн embed харагдац тохируулах")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(event=[
        app_commands.Choice(name="Гишүүн орж ирэхэд", value="member_join"),
        app_commands.Choice(name="Гишүүн гарахад", value="member_leave"),
    ])
    async def automation_embed(self, interaction: discord.Interaction, event: app_commands.Choice[str], title: str, color_hex: str = "FF4FA3"):
        try:
            color = int(color_hex.removeprefix("#"), 16)
            if not 0 <= color <= 0xFFFFFF:
                raise ValueError
        except ValueError:
            return await interaction.response.send_message("❌ Color нь `FF4FA3` шиг 6 оронтой hex байх ёстой.", ephemeral=True)
        changed = await self.bot.db_manager.update("automation_rules", {"guild_id": str(interaction.guild_id), "event_name": event.value}, {"embed_title": title[:256], "embed_color": color, "updated_at": int(time.time())})
        if not changed:
            return await interaction.response.send_message("❌ Эхлээд `/automation_setup` хийж rule үүсгэнэ үү.", ephemeral=True)
        await interaction.response.send_message("✅ Embed харагдац хадгалагдлаа. `/automation_test` ашиглан шалгана уу.", ephemeral=True)

    @app_commands.command(name="automation_disable", description="Automation event унтраах")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(event=[
        app_commands.Choice(name="Гишүүн орж ирэхэд", value="member_join"),
        app_commands.Choice(name="Гишүүн гарахад", value="member_leave"),
    ])
    async def automation_disable(self, interaction: discord.Interaction, event: app_commands.Choice[str]):
        changed = await self.bot.db_manager.update(
            "automation_rules", {"guild_id": str(interaction.guild_id), "event_name": event.value},
            {"enabled": False, "updated_at": int(time.time())},
        )
        if not changed:
            return await interaction.response.send_message("❌ Энэ event-д тохиргоо байхгүй.", ephemeral=True)
        await interaction.response.send_message("✅ Automation унтарлаа.", ephemeral=True)

    @app_commands.command(name="automation_status", description="Automation тохиргоо харах")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def automation_status(self, interaction: discord.Interaction):
        rules = await self.bot.db_manager.fetch_all("automation_rules", {"guild_id": str(interaction.guild_id)})
        if not rules:
            return await interaction.response.send_message(embed=accent_embed("✦ Automation", "Одоогоор идэвхтэй rule алга."), ephemeral=True)
        lines = []
        for rule in rules:
            state = "🟢" if rule.get("enabled") else "⚪"
            log = f" • log: <#{rule['log_channel_id']}>" if rule.get("log_channel_id") else ""
            lines.append(f"{state} **{EVENTS.get(rule['event_name'], rule['event_name'])}** → <#{rule['channel_id']}>{log}")
        await interaction.response.send_message(embed=accent_embed("✦ Automation", "\n".join(lines)), ephemeral=True)

    async def _run(self, member: discord.Member, event_name: str):
        try:
            rule = await self.bot.db_manager.fetch_one(
                "automation_rules",
                {"guild_id": str(member.guild.id), "event_name": event_name, "enabled": True},
            )
        except DatabaseSchemaError:
            # A member event must never become an unhandled Discord event
            # exception while PostgREST is waiting for a schema-cache reload
            # or the production migration is being applied.
            return
        if not rule:
            return
        channel = member.guild.get_channel(int(rule["channel_id"]))
        if not isinstance(channel, discord.TextChannel):
            await self._record(rule, member.guild.id, event_name, "skipped", "Configured channel was unavailable")
            return
        message = (rule["message_template"]
            .replace("{member}", member.mention)
            .replace("{server}", member.guild.name)
            .replace("{count}", str(member.guild.member_count or 0)))
        try:
            if rule.get("embed_title"):
                await channel.send(embed=discord.Embed(title=rule["embed_title"], description=message, color=rule.get("embed_color") or 0xFF4FA3), allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            else:
                await channel.send(message, allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            await self._record(rule, member.guild.id, event_name, "sent", None)
        except discord.HTTPException as exc:
            await self._record(rule, member.guild.id, event_name, "failed", str(exc)[:500])

    async def _record(self, rule, guild_id: int, event_name: str, status: str, detail: str | None):
        await self.bot.db_manager.insert("automation_runs", {
            "rule_id": rule["id"], "guild_id": str(guild_id), "event_name": event_name,
            "status": status, "detail": detail, "created_at": int(time.time()),
        })
        log_channel_id = rule.get("log_channel_id")
        guild = self.bot.get_guild(int(guild_id))
        log_channel = guild.get_channel(int(log_channel_id)) if guild and log_channel_id else None
        if isinstance(log_channel, discord.TextChannel):
            icon = {"sent": "✅", "skipped": "⚠️", "failed": "❌"}[status]
            await log_channel.send(embed=accent_embed(
                f"{icon} Automation log",
                f"**Event:** {EVENTS.get(event_name, event_name)}\n**Status:** {status}\n{detail or 'Message амжилттай илгээгдлээ.'}",
            ))

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._run(member, "member_join")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self._run(member, "member_leave")


async def setup(bot):
    await bot.add_cog(WebhookAutomation(bot))
