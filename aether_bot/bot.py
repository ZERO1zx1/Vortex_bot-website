"""Aether Discord bot — entry point.

Ажиллуулах::

    cp .env.example .env    # DISCORD_TOKEN-оо бөглөнө
    python bot.py

`setup_hook` дотор DB-г холбож, migration-уудыг ажиллуулж, HTTP rate
limiter-ийг суулгаад cog-уудыг ачаална. Ганц process, ганц event loop.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from core.database import Database
from core.event_bus import EventBus
from core.rate_limiter import install_http_guard
from repositories.user_repo import UserRepository
from services.rpg.skill_service import SkillService

log = logging.getLogger(__name__)

COGS = (
    "cogs.health",
    "cogs.economy",
    "cogs.skills",
    "cogs.admin",
)


async def get_prefix(bot: commands.Bot, message: discord.Message) -> list[str]:
    """Сервер бүрийн `guild_settings.prefix`, эс бөгөөс env default."""
    prefix = config.DEFAULT_PREFIX
    db = getattr(bot, "db", None)
    if message.guild is not None and isinstance(db, Database):
        try:
            stored = await db.fetchval(
                "SELECT prefix FROM guild_settings WHERE guild_id = ?",
                (message.guild.id,),
            )
        except Exception:  # DB хараахан бэлэн биш — default руу буулгана
            log.debug("Guild prefix уншиж чадсангүй", exc_info=True)
        else:
            if stored:
                prefix = str(stored)
    return commands.when_mentioned_or(prefix)(bot, message)


class AetherBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True  # prefix командуудад шаардлагатай
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        self.db = Database(config.DB_PATH, migrations_dir=config.MIGRATIONS_DIR)
        self.user_repo = UserRepository(self.db)
        self.event_bus = EventBus()
        self.skills = SkillService(
            self.db,
            user_repo=self.user_repo,
            event_bus=self.event_bus,
        )
        self.limiters: dict[str, object] = {}

    async def setup_hook(self) -> None:
        await self.db.connect()
        try:
            self.limiters = install_http_guard(
                self,
                max_rate=config.RATE_LIMIT_PER_SECOND,
            )
            for extension in COGS:
                await self.load_extension(extension)

            if config.GUILD_ID:
                guild = discord.Object(id=config.GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                log.info(
                    "Guild %s руу %s команд sync хийлээ", config.GUILD_ID, len(synced)
                )
            else:
                synced = await self.tree.sync()
                log.info("%s глобал команд sync хийлээ", len(synced))
        except BaseException:
            await self.db.close()
            raise

    async def on_ready(self) -> None:
        log.info(
            "Aether бэлэн: %s (id=%s, guilds=%s)",
            self.user,
            getattr(self.user, "id", "?"),
            len(self.guilds),
        )

    async def close(self) -> None:
        if self.db.connected:
            await self.db.close()
        await super().close()


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        token = config.require_token()
    except config.ConfigError as exc:
        raise SystemExit(f"Тохиргооны алдаа: {exc}") from exc

    bot = AetherBot()
    try:
        bot.run(token, log_handler=None)
    except discord.LoginFailure as exc:
        raise SystemExit(
            "Discord login амжилтгүй — DISCORD_TOKEN болон privileged "
            "Message Content intent-ийг шалгана уу."
        ) from exc


if __name__ == "__main__":
    main()
