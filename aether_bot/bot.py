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
from repositories.cooldown_repo import CooldownRepository
from repositories.guild_repo import GuildRepository
from repositories.log_repo import LogRepository
from repositories.shop_repo import ShopRepository
from repositories.skill_repo import SkillRepository
from repositories.user_repo import UserRepository
from services.casino.blackjack_service import BlackjackService
from services.casino.crash_service import CrashService
from services.casino.lottery_service import LotteryService
from services.casino.minefield_service import MinefieldService
from services.casino.roulette_service import RouletteService
from services.casino.slots_service import SlotsService
from services.economy.crime_service import CrimeService
from services.economy.income_service import IncomeService
from services.economy.jail_service import JailService
from services.economy.wallet_service import WalletService
from services.games.adventure_service import AdventureService
from services.games.boss_service import BossService
from services.games.duel_service import DuelService
from services.games.hunt_fish_service import HuntFishService
from services.rpg.inventory_service import InventoryService
from services.rpg.level_service import LevelService
from services.rpg.shop_service import ShopService
from services.rpg.skill_service import SkillService

log = logging.getLogger(__name__)

COGS = (
    "cogs.system.help",
    "cogs.system.events",
    "cogs.system.admin",
    "cogs.economy.wallet",
    "cogs.economy.income",
    "cogs.economy.crime",
    "cogs.rpg.profile",
    "cogs.rpg.skills",
    "cogs.rpg.shop",
    "cogs.rpg.inventory",
    "cogs.casino.slots",
    "cogs.casino.blackjack",
    "cogs.casino.roulette",
    "cogs.casino.minefield",
    "cogs.casino.coinflip",
    "cogs.casino.crash",
    "cogs.casino.lottery",
    "cogs.games.duel",
    "cogs.games.adventure",
    "cogs.games.hunt_fish",
    "cogs.games.boss",
)


async def get_prefix(bot: commands.Bot, message: discord.Message) -> list[str]:
    """Сервер бүрийн `guild_settings.prefix`, эс бөгөөс env default."""
    prefix = config.DEFAULT_PREFIX
    db = getattr(bot, "guild_repo", None)
    if message.guild is not None and isinstance(db, GuildRepository):
        try:
            stored = await db.prefix(message.guild.id)
        except Exception:  # DB хараахан бэлэн биш — default руу буулгана
            log.debug("Guild prefix уншиж чадсангүй", exc_info=True)
        else:
            prefix = stored
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
        self.guild_repo = GuildRepository(self.db)
        self.logs = LogRepository(self.db)
        self.cooldowns = CooldownRepository(self.db)
        self.shop_repo = ShopRepository(self.db)
        self.skill_repo = SkillRepository(self.db)

        self.wallet = WalletService(
            self.db, users=self.user_repo, guilds=self.guild_repo, logs=self.logs
        )
        self.levels = LevelService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            shop=self.shop_repo,
            event_bus=self.event_bus,
        )
        self.levels.subscribe(self.event_bus)
        self.skills = SkillService(
            self.db,
            user_repo=self.user_repo,
            event_bus=self.event_bus,
        )
        self.income = IncomeService(
            self.db,
            users=self.user_repo,
            cooldowns=self.cooldowns,
            logs=self.logs,
            skills=self.skills,
            level_service=self.levels,
            event_bus=self.event_bus,
        )
        self.jail = JailService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            event_bus=self.event_bus,
        )
        self.crime = CrimeService(
            self.db,
            users=self.user_repo,
            cooldowns=self.cooldowns,
            logs=self.logs,
            skills=self.skills,
            jail=self.jail,
            event_bus=self.event_bus,
        )
        self.shop = ShopService(
            self.db,
            users=self.user_repo,
            shop=self.shop_repo,
            logs=self.logs,
            skills=self.skills,
        )
        self.inventory = InventoryService(
            self.db,
            users=self.user_repo,
            shop=self.shop_repo,
            cooldowns=self.cooldowns,
            skills=self.skills,
        )
        self.slots = SlotsService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.blackjack = BlackjackService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.roulette = RouletteService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.minefield = MinefieldService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.crash = CrashService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            skills=self.skills,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.lottery = LotteryService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            wallet=self.wallet,
            skills=self.skills,
            event_bus=self.event_bus,
        )
        self.duel = DuelService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            wallet=self.wallet,
            skills=self.skills,
            event_bus=self.event_bus,
        )
        self.adventure = AdventureService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            cooldowns=self.cooldowns,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.huntfish = HuntFishService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            cooldowns=self.cooldowns,
            wallet=self.wallet,
            event_bus=self.event_bus,
        )
        self.boss = BossService(
            self.db,
            users=self.user_repo,
            logs=self.logs,
            cooldowns=self.cooldowns,
            wallet=self.wallet,
            skills=self.skills,
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
            "Aether бэлэн: %s (id=%s)",
            self.user,
            getattr(self.user, "id", "?"),
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
