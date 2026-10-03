import asyncio
import inspect
import logging
import random
import uuid
from datetime import datetime, timezone

import discord
from discord.ext import commands

from src.core.exceptions import DatabaseSchemaError
from src.utils.constants import (
    ERROR_COLOR,
    GOLD_COLOR,
    INFO_COLOR,
    SUCCESS_COLOR,
    WARNING_COLOR,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_HP = 100
MAX_ENERGY = 3
WIN_REWARD_MIN = 200
WIN_REWARD_MAX = 500
PROFILE_TABLE = "anime_clash_profiles"
HEROES = {
    "samurai": {"name": "⚔️ Samurai", "hp": 115, "attack": 3, "skill": 0, "focus": 0},
    "mage": {"name": "🔮 Mage", "hp": 90, "attack": 0, "skill": 12, "focus": 0},
    "assassin": {"name": "🌑 Assassin", "hp": 95, "attack": 6, "skill": 4, "focus": 0},
    "healer": {"name": "🌸 Healer", "hp": 120, "attack": 0, "skill": 0, "focus": 8},
}
DIFFICULTIES = {
    "easy": {"name": "Easy", "enemy_hp": 85, "damage": 0.80, "reward": 0.8, "xp": 30},
    "normal": {"name": "Normal", "enemy_hp": 100, "damage": 1.0, "reward": 1.0, "xp": 50},
    "hard": {"name": "Hard", "enemy_hp": 135, "damage": 1.25, "reward": 1.6, "xp": 90},
    "daily": {"name": "Daily Boss", "enemy_hp": 130, "damage": 1.15, "reward": 2.2, "xp": 150},
}
ENEMIES = (
    ("🌑 Shadow Ronin", "Сүүдрийн сэлэмчин"),
    ("⚡ Neon Shogun", "Цахилгаан шогун"),
    ("🔮 Celestial Witch", "Оддын шулам"),
    ("👹 Mecha Oni", "Төмөр они"),
)


def hp_bar(value: int, maximum: int = DEFAULT_MAX_HP) -> str:
    if value <= 0:
        filled = 0
    elif value >= maximum:
        filled = 10
    else:
        filled = max(1, value * 10 // maximum)
    return "▰" * filled + "▱" * (10 - filled)


class AnimeClashGame:
    def __init__(self, user_id: int, enemy=None, hero: str = "samurai", difficulty: str = "normal"):
        if hero not in HEROES:
            raise ValueError(f"Unknown hero: {hero}")
        if difficulty not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty}")
        self.hero_key = hero
        self.hero = HEROES[hero]
        self.difficulty_key = difficulty
        self.difficulty = DIFFICULTIES[difficulty]
        self.user_id = user_id
        self.enemy_name, self.enemy_title = enemy or random.choice(ENEMIES)
        self.max_hp = self.hero["hp"]
        self.enemy_max_hp = self.difficulty["enemy_hp"]
        self.player_hp = self.max_hp
        self.enemy_hp = self.enemy_max_hp
        self.energy = 0
        self.finished = False
        self.settled = False
        self.result = None
        self.turn = 0
        self.pending_reward = None
        self.last_action = None
        self.chain = 0
        self.best_chain = 0
        self.burn_turns = 0
        # Retry-н хооронд тогтсон, давхар credit-ээс хамгаалах reference-ийн суурь.
        self.game_id = uuid.uuid4().hex[:12]

    def take_turn(self, action: str) -> dict:
        if self.finished:
            return {"status": "finished"}
        if action == "skill" and self.energy < MAX_ENERGY:
            return {"status": "no_energy"}

        healed = 0
        guarded = action == "guard"
        burn_damage = 0
        combo_name = None

        # Burn is a two-turn damage-over-time effect after the casting turn.
        if self.burn_turns > 0 and self.enemy_hp > 0:
            burn_damage = min(5, self.enemy_hp)
            self.enemy_hp -= burn_damage
            self.burn_turns -= 1
            if self.enemy_hp == 0:
                self.turn += 1
                self.finished = True
                self.result = "win"
                return {
                    "status": "win", "dealt": 0, "received": 0,
                    "healed": 0, "guarded": False,
                    "burn_damage": burn_damage, "combo_name": None,
                    "burn_only": True,
                }

        self.turn += 1

        if action == self.last_action:
            self.chain = 1
        else:
            self.chain += 1
        self.best_chain = max(self.best_chain, self.chain)

        if action == "attack":
            dealt = random.randint(16, 24) + self.hero["attack"]
            if self.last_action == "guard":
                dealt += 8
                combo_name = "COUNTER SLASH"
            self.energy = min(MAX_ENERGY, self.energy + 1)
        elif action == "guard":
            dealt = random.randint(3, 6)
        elif action == "focus":
            dealt = 0
            old_hp = self.player_hp
            self.player_hp = min(self.max_hp, self.player_hp + random.randint(14, 20) + self.hero["focus"])
            healed = self.player_hp - old_hp
            self.energy = min(MAX_ENERGY, self.energy + 2)
        elif action == "skill":
            dealt = random.randint(35, 50) + self.hero["skill"]
            if self.last_action == "focus":
                dealt += 12
                combo_name = "SOUL BURST"
            self.energy = 0
            self.burn_turns = 2
        else:
            raise ValueError(f"Unknown action: {action}")

        self.enemy_hp = max(0, self.enemy_hp - dealt)
        received = 0
        if self.enemy_hp == 0:
            self.finished = True
            self.result = "win"
        else:
            received = max(1, int(random.randint(12, 20) * self.difficulty["damage"]))
            if guarded:
                received = max(1, received * 15 // 100)
            self.player_hp = max(0, self.player_hp - received)
            if self.player_hp == 0:
                self.finished = True
                self.result = "loss"

        self.last_action = action

        return {
            "status": self.result or "continue",
            "dealt": dealt,
            "received": received,
            "healed": healed,
            "guarded": guarded,
            "burn_damage": burn_damage,
            "combo_name": combo_name,
            "burn_only": False,
        }


class AnimeClashView(discord.ui.View):
    def __init__(self, bot, ctx, game: AnimeClashGame):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.game = game
        self.message = None
        self._turn_lock = asyncio.Lock()

    def build_embed(self, title: str, description: str, color: int) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(
            name=f"{self.game.hero['name']} • {self.ctx.author.display_name}",
            value=f"{hp_bar(self.game.player_hp, self.game.max_hp)} **{self.game.player_hp}/{self.game.max_hp} HP**\n"
                  f"⚡ Energy: **{self.game.energy}/{MAX_ENERGY}** • 🔗 Chain: **{self.game.chain}**",
            inline=False,
        )
        embed.add_field(
            name=self.game.enemy_name,
            value=f"{hp_bar(self.game.enemy_hp, self.game.enemy_max_hp)} **{self.game.enemy_hp}/{self.game.enemy_max_hp} HP**\n"
                  f"_{self.game.enemy_title} • {self.game.difficulty['name']}_",
            inline=False,
        )
        embed.set_footer(text=f"Turn {self.game.turn} • Ultimate-д {MAX_ENERGY} Energy хэрэгтэй")
        return embed

    async def _credit_reward(self, amount: int) -> bool:
        economy = self.bot.get_cog("Economy")
        if economy is None:
            logger.error("anime clash reward skipped: Economy cog is unavailable")
            return False

        # game_id нь game instance-д тогтсон тул retry хийгдсэн ч ижил key.
        # amount-ыг оруулаагүй — нэг game = нэг reward (semantic).
        reference = (
            f"animeclash:{self.game.user_id}:{self.ctx.guild.id}:{self.game.game_id}"
        )

        # Economy.update_balance нь reference kwarg-ийг дэмждэг эсэхийг нэг удаа шалга.
        accepts_reference = False
        try:
            sig = inspect.signature(economy.update_balance)
            accepts_reference = (
                "reference" in sig.parameters
                or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                )
            )
        except (TypeError, ValueError):
            accepts_reference = False

        last_exc: Exception | None = None
        for attempt in range(1, 4):
            try:
                if accepts_reference:
                    await economy.update_balance(
                        self.game.user_id,
                        self.ctx.guild.id,
                        amount,
                        reference=reference,
                    )
                else:
                    await economy.update_balance(
                        self.game.user_id, self.ctx.guild.id, amount
                    )
                return True
            except Exception as exc:
                last_exc = exc
                if isinstance(exc, DatabaseSchemaError):
                    logger.exception(
                        "anime clash reward unavailable: required economy migration/RPC is missing"
                    )
                    break
                logger.warning(
                    "anime clash reward attempt %d/3 failed for user %s in guild %s: %s",
                    attempt, self.game.user_id, self.ctx.guild.id, exc,
                    exc_info=True,
                )
                if attempt < 3:
                    await asyncio.sleep(0.5 * attempt)

        logger.error(
            "anime clash reward exhausted retries for user %s in guild %s",
            self.game.user_id, self.ctx.guild.id, exc_info=last_exc,
        )
        return False

    async def handle_action(self, interaction: discord.Interaction, action: str):
        if interaction.user.id != self.game.user_id:
            return await interaction.response.send_message("❌ Энэ тулаан таных биш!", ephemeral=True)

        async with self._turn_lock:
            if self.game.finished or self.game.settled:
                return await interaction.response.send_message("❌ Тулаан аль хэдийн дууссан.", ephemeral=True)

            result = self.game.take_turn(action)
            if result["status"] == "no_energy":
                return await interaction.response.send_message(
                    f"⚡ Ultimate ашиглахын тулд {MAX_ENERGY} Energy цуглуулна уу.", ephemeral=True
                )

            action_names = {
                "attack": "⚔️ Дайралт",
                "guard": "🛡️ Хамгаалалт",
                "focus": "✨ Focus",
                "skill": "🔥 ULTIMATE",
            }
            if result.get("burn_only"):
                details = ["🔥 Burn effect дайсныг дуусгалаа!"]
            elif result["dealt"]:
                details = [f"**{action_names[action]}** ашиглаж **{result['dealt']}** damage өглөө."]
            else:
                details = [f"**{action_names[action]}** ашиглав."]
            if result["healed"]:
                details.append(f"💚 **{result['healed']} HP** сэргээв.")
            if result["combo_name"]:
                details.append(f"🔗 **{result['combo_name']}** special chain идэвхжив!")
            if result["burn_damage"] and not result.get("burn_only"):
                details.append(f"🔥 Burn effect **{result['burn_damage']}** нэмэлт damage өглөө.")
            if result["received"]:
                details.append(f"{self.game.enemy_name} хариу довтолж **{result['received']}** damage өглөө.")

            deferred = False
            if result["status"] == "win":
                self.game.settled = True
                if self.game.pending_reward is None:
                    base_reward = random.randint(WIN_REWARD_MIN, WIN_REWARD_MAX)
                    hp_bonus = 0.5 + 0.5 * (self.game.player_hp / self.game.max_hp)
                    self.game.pending_reward = int(
                        base_reward * self.game.difficulty["reward"] * hp_bonus
                    )
                reward = self.game.pending_reward
                # Reward storage can exceed Discord's response window.
                await interaction.response.defer()
                deferred = True
                credited = await self._credit_reward(reward)
                if not credited:
                    self.game.settled = False
                    self.game.finished = False
                    self.game.result = None
                    return await interaction.followup.send(
                        "⚠️ Шагнал хадгалахад алдаа гарлаа. Дахин оролдоно уу.", ephemeral=True
                    )
                self.game.pending_reward = None
                details.append(f"\n🏆 Ялалтын шагнал: **{reward:,} мөнгө**")
                details.append(f"⭐ XP: **+{self.game.difficulty['xp']}**")
                await self._record_result(won=True, reward=reward)
                embed = self.build_embed("🏆 ANIME CLASH — ЯЛАЛТ!", "\n".join(details), SUCCESS_COLOR)
                self._finish()
            elif result["status"] == "loss":
                self.game.settled = True
                await self._record_result(won=False, reward=0)
                embed = self.build_embed("💀 ANIME CLASH — ЯЛАГДАЛ", "\n".join(details), ERROR_COLOR)
                self._finish()
            else:
                embed = self.build_embed("⚔️ ANIME CLASH", "\n".join(details), GOLD_COLOR)

            if deferred:
                await interaction.edit_original_response(embed=embed, view=self)
            else:
                await interaction.response.edit_message(embed=embed, view=self)

    async def _record_result(self, won: bool, reward: int):
        cog = self.bot.get_cog("AnimeClash")
        if cog is None:
            return
        try:
            await cog.record_result(self.ctx, self.game, won, reward)
        except Exception as exc:
            logger.warning("anime clash profile update failed: %s", exc, exc_info=True)

    def _finish(self):
        for child in self.children:
            child.disabled = True
        self.stop()

    @discord.ui.button(label="ATTACK", emoji="⚔️", style=discord.ButtonStyle.danger)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "attack")

    @discord.ui.button(label="GUARD", emoji="🛡️", style=discord.ButtonStyle.primary)
    async def guard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "guard")

    @discord.ui.button(label="FOCUS", emoji="✨", style=discord.ButtonStyle.secondary)
    async def focus(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "focus")

    @discord.ui.button(label="ULTIMATE", emoji="🔥", style=discord.ButtonStyle.success)
    async def skill(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_action(interaction, "skill")

    async def on_timeout(self):
        async with self._turn_lock:
            if self.game.finished or self.game.settled:
                return
            self.game.finished = True
            self.game.settled = True
        await self._record_result(won=False, reward=0)
        self._finish()
        if self.message:
            daily_note = " Daily Boss оролдлого зарцуулагдлаа." if self.game.difficulty_key == "daily" else ""
            embed = self.build_embed(
                "⏰ ANIME CLASH — TIMEOUT",
                f"{self.ctx.author.mention}, тулааны хугацаа дуусаж ялагдалд тооцогдлоо.{daily_note}",
                WARNING_COLOR,
            )
            try:
                await self.message.edit(embed=embed, view=self)
            except discord.HTTPException as exc:
                logger.warning("anime clash timeout edit failed: %s", exc)


class AnimeClash(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def level_for_xp(xp: int) -> int:
        return xp // 250 + 1

    async def get_profile(self, user_id: int, guild_id: int) -> dict:
        row = await self.bot.db_manager.fetch_one(
            PROFILE_TABLE, {"user_id": str(user_id), "guild_id": str(guild_id)}
        )
        return row or {
            "user_id": str(user_id),
            "guild_id": str(guild_id),
            "xp": 0,
            "level": 1,
            "wins": 0,
            "losses": 0,
            "best_combo": 0,
            "total_reward": 0,
            "favorite_hero": "samurai",
            "last_daily_date": None,
        }

    async def record_result(self, ctx, game: AnimeClashGame, won: bool, reward: int):
        profile = await self.get_profile(ctx.author.id, ctx.guild.id)
        xp_gain = game.difficulty["xp"] if won else 10
        xp = int(profile.get("xp", 0) or 0) + xp_gain
        profile.update({
            "xp": xp,
            "level": self.level_for_xp(xp),
            "wins": int(profile.get("wins", 0) or 0) + (1 if won else 0),
            "losses": int(profile.get("losses", 0) or 0) + (0 if won else 1),
            "best_combo": max(int(profile.get("best_combo", 0) or 0), game.best_chain),
            "total_reward": int(profile.get("total_reward", 0) or 0) + reward,
            "favorite_hero": game.hero_key,
        })
        await self.bot.db_manager.upsert(
            PROFILE_TABLE, profile, on_conflict="user_id,guild_id"
        )

    async def claim_daily_attempt(self, user_id: int, guild_id: int) -> bool:
        profile = await self.get_profile(user_id, guild_id)
        today = datetime.now(timezone.utc).date().isoformat()
        if profile.get("last_daily_date") == today:
            return False
        profile["last_daily_date"] = today
        await self.bot.db_manager.upsert(
            PROFILE_TABLE, profile, on_conflict="user_id,guild_id"
        )
        return True

    async def check_hunger_mood(self, ctx) -> bool:
        economy = self.bot.get_cog("Economy")
        if economy is None:
            return True
        if await economy.is_in_prison(ctx.author.id, ctx.guild.id):
            await ctx.send("🚔 Шоронд байхдаа тоглох боломжгүй.")
            return False
        hunger, mood = await economy.get_hunger_mood(ctx.author.id, ctx.guild.id)
        if hunger >= 80:
            await ctx.send(f"🍔 {ctx.author.mention}, та хэт өлсөж байна! `A!eat` хийгээрэй.")
            return False
        if mood >= 80:
            await ctx.send(f"😡 {ctx.author.mention}, та хэт ууртай байна! `A!relax` хийгээрэй.")
            return False
        return True

    async def start_battle(self, ctx, hero: str, difficulty: str):
        hero = hero.lower()
        difficulty = difficulty.lower()
        if hero not in HEROES:
            choices = ", ".join(HEROES)
            return await ctx.send(f"❌ Дүр олдсонгүй. Сонголт: `{choices}`")
        if difficulty not in DIFFICULTIES or difficulty == "daily":
            return await ctx.send("❌ Difficulty: `easy`, `normal`, эсвэл `hard` сонгоно уу.")

        game = AnimeClashGame(ctx.author.id, hero=hero, difficulty=difficulty)
        await self.send_battle(ctx, game)

    async def send_battle(self, ctx, game: AnimeClashGame):
        view = AnimeClashView(self.bot, ctx, game)
        embed = view.build_embed(
            "⚔️ ANIME CLASH — 魂の決闘",
            f"{ctx.author.mention}, **{game.enemy_name}** чамайг дуэльд дуудлаа!\n"
            f"Class: **{game.hero['name']}** • Difficulty: **{game.difficulty['name']}**\n\n"
            "⚔️ Attack — damage + 1 Energy\n"
            "🛡️ Guard — хүчтэй хамгаалалт, Energy өгөхгүй\n"
            "✨ Focus — HP нөхөх + 2 Energy\n"
            f"🔥 Ultimate — {MAX_ENERGY} Energy, Burn effect\n"
            "🔗 Action-аа сольж Chain өсгөнө; Guard → Attack болон Focus → Ultimate special chain-тай",
            INFO_COLOR,
        )
        view.message = await ctx.send(embed=embed, view=view)

    @commands.command(name="animeclash", aliases=["clash", "ac"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def animeclash(self, ctx, hero: str = "samurai", difficulty: str = "normal"):
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")

        if not await self.check_hunger_mood(ctx):
            return

        await self.start_battle(ctx, hero, difficulty)

    @commands.command(name="dailyboss", aliases=["dboss"])
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def dailyboss(self, ctx, hero: str = "samurai"):
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")
        if hero.lower() not in HEROES:
            return await ctx.send(f"❌ Дүр олдсонгүй. Сонголт: `{', '.join(HEROES)}`")
        if not await self.check_hunger_mood(ctx):
            return
        try:
            if not await self.claim_daily_attempt(ctx.author.id, ctx.guild.id):
                return await ctx.send("⏳ Daily Boss-оо өнөөдөр аль хэдийн тоглосон байна.")
        except Exception:
            logger.exception("anime clash daily claim failed")
            return await ctx.send("⚠️ Daily Boss мэдээлэл хадгалахад алдаа гарлаа.")

        index = datetime.now(timezone.utc).date().toordinal() % len(ENEMIES)
        enemy = ENEMIES[index]
        game = AnimeClashGame(ctx.author.id, enemy=enemy, hero=hero.lower(), difficulty="daily")
        await self.send_battle(ctx, game)

    @commands.command(name="animeheroes", aliases=["heroes"])
    async def animeheroes(self, ctx):
        lines = [
            "⚔️ `samurai` — 115 HP, +3 Attack",
            "🔮 `mage` — 90 HP, +12 Ultimate",
            "🌑 `assassin` — 95 HP, +6 Attack, +4 Ultimate",
            "🌸 `healer` — 120 HP, +8 Focus heal",
        ]
        await ctx.send(embed=discord.Embed(
            title="🎴 Anime Clash Classes",
            description="\n".join(lines),
            color=INFO_COLOR,
        ))

    @commands.command(name="animeprofile", aliases=["aprofile"])
    async def animeprofile(self, ctx):
        if ctx.guild is None:
            return await ctx.send("❌ Зөвхөн серверт ашиглана уу.")
        try:
            profile = await self.get_profile(ctx.author.id, ctx.guild.id)
        except Exception:
            logger.exception("anime clash profile fetch failed")
            return await ctx.send("⚠️ Profile мэдээлэл ачаалж чадсангүй.")
        xp = int(profile.get("xp", 0) or 0)
        level = self.level_for_xp(xp)
        next_level_xp = level * 250
        embed = discord.Embed(title="🎴 Anime Clash Profile", color=GOLD_COLOR)
        embed.description = f"{ctx.author.mention} • Level **{level}** • XP **{xp}/{next_level_xp}**"
        embed.add_field(name="🏆 Wins", value=str(profile.get("wins", 0) or 0))
        embed.add_field(name="💀 Losses", value=str(profile.get("losses", 0) or 0))
        embed.add_field(name="🔗 Best chain", value=str(profile.get("best_combo", 0) or 0))
        embed.add_field(name="💰 Rewards", value=f"{int(profile.get('total_reward', 0) or 0):,}")
        embed.add_field(name="🎭 Last hero", value=str(profile.get("favorite_hero", "samurai")))
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AnimeClash(bot))
