# -*- coding: utf-8 -*-
"""Хэлний тохиргоо — A!lang mn|en"""
import discord
from discord.ext import commands
from discord import app_commands
from utils.constants import DEFAULT_PREFIX, EMBED_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, GOLD_COLOR, INFO_COLOR
from utils.branding import footer_text
from utils.supabase_cog import SupabaseCog
from utils import i18n


class LangCog(SupabaseCog, name="Хэл / Language"):
    """Серверийн хэлийг Монгол (mn) эсвэл Англи (en) болгож солих."""

    @commands.command(name="lang", help="Серверийн хэл солих: A!lang mn эсвэл A!lang en")
    @commands.has_guild_permissions(manage_guild=True)
    async def lang_text(self, ctx: commands.Context, new_lang: str = "") -> None:
        if new_lang.lower() not in i18n.SUPPORTED_LANGS:
            embed = discord.Embed(
                color=ERROR_COLOR,
                description=i18n.t(ctx.guild.id, "core.lang_invalid", given=new_lang or "(хоосон)"),
            )
            embed.set_footer(text=footer_text())
            await ctx.send(embed=embed)
            return

        new_lang = new_lang.lower()
        await i18n.set_guild_lang(ctx.guild.id, new_lang)
        # Хэл солигдсоны дараа: core.lang_changed шинэ хэлээр хэлэлбэл зөв
        embed = discord.Embed(color=SUCCESS_COLOR, description=i18n.t_direct(new_lang, "core.lang_changed", new=new_lang.upper()))
        embed.add_field(
            name=i18n.t_direct(new_lang, "core.lang_current", lang_mn=i18n.t_direct(new_lang, "core.lang_mn"), lang_en=i18n.t_direct(new_lang, "core.lang_en")),
            value=i18n.t_direct(new_lang, "core.lang_changed_note", mn="Командын хариунууд одооноос энэ хэлээр ирнэ.", en="Command responses will now come in this language."),
            inline=False,
        )
        embed.set_footer(text=footer_text())
        await ctx.send(embed=embed)

    @lang_text.error
    async def lang_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(color=WARNING_COLOR, description=i18n.t(ctx.guild.id, "core.lang_no_perm"))
            embed.set_footer(text=footer_text())
            await ctx.send(embed=embed)

    @app_commands.command(name="lang", description="Change server language: /lang mn or /lang en")
    @app_commands.describe(lang="mn эсвэл en")
    @app_commands.choices(lang=[
        app_commands.Choice(name="Монгол (mn)", value="mn"),
        app_commands.Choice(name="English (en)", value="en"),
    ])
    @app_commands.checks.has_permissions(manage_guild=True)
    async def lang_slash(self, interaction: discord.Interaction, lang: app_commands.Choice[str]) -> None:
        value = lang.value
        await i18n.set_guild_lang(interaction.guild_id, value)
        embed = discord.Embed(color=SUCCESS_COLOR, description=i18n.t(interaction.guild_id, "core.lang_changed", new=value.upper()))
        embed.set_footer(text=footer_text())
        await interaction.response.send_message(embed=embed)

    @lang_slash.error
    async def lang_slash_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            embed = discord.Embed(color=WARNING_COLOR, description=i18n.t(interaction.guild_id, "core.lang_no_perm"))
            embed.set_footer(text=footer_text())
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(LangCog(bot))
