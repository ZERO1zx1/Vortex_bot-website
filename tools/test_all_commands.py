"""Invoke every hybrid command cog-side by simulating a Message and a minimal
Context, capturing exceptions without sending real Discord traffic.

This tests the handler Python paths (permission checks, db reads, validation)
without needing a real human member in the guild. Messages from a test user id
flow through the message dispatch like a normal prefix invocation would, but
we call the callbacks directly with a fake ctx so the results are deterministic
and logged to a file.
"""
import asyncio
import inspect
import logging
import os
import sys
import traceback
from unittest.mock import MagicMock

import discord
from discord.ext import commands

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from main import MyBot

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("cmdtest")

BOT_OWNER_ID = 1468270807686840543  # the real owner from logs (Light)
GUILD_ID = 1501605621584363720


class FakeRole:
    def __init__(self, name="admin", position=100):
        self.id = 1
        self.name = name
        self.position = position
    def __ge__(self, other): return self.position >= getattr(other, "position", 0)
    def __le__(self, other): return self.position <= getattr(other, "position", 0)
    def __gt__(self, other): return self.position > getattr(other, "position", 0)
    def __lt__(self, other): return self.position < getattr(other, "position", 0)
    @property
    def mention(self): return f"<@&{self.id}>"

class FakeChannel:
    """Duck-typed text channel that sends safely (no real Discord traffic)."""
    def __init__(self, name="cmd-test"):
        self.id = 1
        self.name = name
        self.mention = f"<#{self.id}>"
        self._sent = []

    async def send(self, *args, **kwargs):
        self._sent.append((args, kwargs))
        return MagicMock(id=1)

    async def edit(self, *args, **kwargs):
        pass

    async def set_permissions(self, *args, **kwargs):
        pass

    def overwrites_for(self, *args, **kwargs):
        return MagicMock()


class FakeMember:
    """Duck-typed guild member — avoids discord.Member init which hits the API."""
    def __init__(self):
        self.id = BOT_OWNER_ID
        self.name = "CmdTest"
        self.discriminator = "0"
        self.bot = True
        self.roles = [FakeRole()]
        self.guild_permissions = discord.Permissions.all()
        self.guild = None
        self.top_role = FakeRole()
        self.display_avatar = MagicMock(url="https://example.com/a.png")
        self.status = discord.Status.online
        self.is_timed_out = MagicMock(return_value=False)
        self.send = FakeChannel().send  # for DM paths
        self.kick = MagicMock()
        self.ban = MagicMock()
        self.unban = MagicMock()
        self.edit = MagicMock()
        self.timeout = MagicMock()
        self.remove_timeout = MagicMock()

    async def kick(self, *a, **kw): pass
    async def ban(self, *a, **kw): pass
    async def unban(self, *a, **kw): pass
    async def edit(self, *a, **kw): pass
    async def timeout(self, *a, **kw): pass
    async def remove_timeout(self, *a, **kw): pass

    @property
    def mention(self):
        return f"<@{self.id}>"

    @property
    def mention(self):
        return f"<@{self.id}>"

    @property
    def display_name(self):
        return "CmdTest"


class FakeCtx:
    def __init__(self, bot, command):
        self.bot = bot
        self.command = command
        self.channel = FakeChannel()
        self.guild = MagicMock(spec=discord.Guild)
        self.guild.id = GUILD_ID
        self.guild.name = "CmdTest Server"
        self.guild.member_count = 125
        self.guild.members = [FakeMember(), FakeMember(), FakeMember()]
        self.guild.roles = [FakeRole("everyone", position=0), FakeRole("admin", position=100)]
        self.guild.text_channels = [self.channel]
        self.guild.voice_channels = []
        self.guild.categories = []
        self.guild.premium_tier = 0
        self.guild.premium_subscription_count = 0
        self.guild.verification_level = discord.VerificationLevel.none
        self.guild.icon = None
        self.guild.banner = None
        self.guild.owner = FakeMember()
        import datetime as _dt
        self.guild.created_at = _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
        self.guild.default_role = FakeRole("everyone", position=0)
        self.guild.me = FakeMember()
        self.guild.get_role = lambda rid: FakeRole() if rid else None
        self.guild.get_member = lambda uid: FakeMember()
        self.guild.fetch_member = lambda uid: asyncio.sleep(0, result=FakeMember())
        self.author = FakeMember()
        self.author.guild = self.guild
        self.prefix = "!"
        self.cog = None
        self.invoked_with = command.name
        self.invoked_subcommand = None
        self.kwargs = {}
        self.args = []
        self.valid = True
        self.result = None

    async def send(self, *args, **kwargs):
        return MagicMock()

    async def edit(self, *args, **kwargs):
        return MagicMock()

    async def defer(self, *args, **kwargs):
        pass

    async def send_help(self, *args, **kwargs):
        pass

    @property
    def clean_prefix(self):
        return "!"


async def run_all():
    bot = MyBot()
    # A non-logged-in bot has no .user (read-only); stub the class attribute.
    bot.__class__.user = property(
        lambda self: type("U", (), {
            "display_avatar": MagicMock(url="https://example.com/bot.png"),
            "mention": "<@123>",
            "name": "Aether", "id": 123,
        })()
    )
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    from database.supabase_manager import SupabaseManager
    db = SupabaseManager()
    db.connect()
    bot.db_manager = db
    bot.config = {"max_balance": 100_000_000}
    # The economy cog's cog_load spawns background tasks via bot.loop;
    # a non-logged-in bot raises AttributeError on .loop, so stub it.
    bot.loop = asyncio.get_event_loop()
    bot.get_guild = lambda gid: None
    bot.wait_until_ready = lambda: asyncio.sleep(0)
    # Exact cog list from main.py
    cogs_to_load = (
        "admin", "avatar_check", "cafe", "carts", "confessions",
        "counting", "economy", "fun", "games", "giveaway",
        "help", "invite_tracker", "leveling", "mafia", "mines",
        "moderation", "pvp", "roles", "shop", "stock",
        "stick", "marriage", "announcement", "tempvoice", "trade",
        "quests", "leaderboard", "casino", "greetings"
    )
    for ext in (f"cogs.{c}" for c in cogs_to_load):
        try:
            await bot.load_extension(ext)
        except Exception as e:
            print(f"[setup] {ext}: {type(e).__name__}: {e}")

    # bot.db_manager already attached above

    results = []
    all_cmds = []
    for cog in bot.cogs.values():
        all_cmds.extend(cog.get_commands())
    print(f"[setup] {len(bot.cogs)} cogs loaded, {len(all_cmds)} commands collected")

    # Collect all hybrid commands registered by the cog
    for cmd in all_cmds:
        if not isinstance(cmd, commands.HybridCommand):
            continue
        # Build kwargs from the command's parameters (skip optional members etc. —
        # provide defaults when available).
        params = {}
        skip = False
        for pname, p in cmd.params.items():
            if pname in ("ctx", "self", "interaction"):
                continue
            if p.default is inspect.Parameter.empty:
                # Required param without a natural test value -> try a small int.
                if p.annotation is discord.Member:
                    params[pname] = FakeMember()
                else:
                    params[pname] = 1000 if p.annotation is int else "test"
        name = cmd.name
        try:
            ctx = FakeCtx(bot, cmd)
            # cmd.callback is the unbound function (self, ctx, ...); bind the cog.
            await cmd.callback(cmd.cog, ctx, **params)
            results.append((name, "OK"))
        except Exception as e:
            tb = traceback.format_exc()
            results.append((name, f"FAIL: {type(e).__name__}: {e}"))
            logger.error("=== %s FAILED ===\n%s", name, tb)

    print("\n===== RESULT SUMMARY =====")
    ok = fail = 0
    for name, status in results:
        print(f"{name}: {status}")
        if status == "OK":
            ok += 1
        else:
            fail += 1
    print(f"\n{ok} OK / {fail} FAILED out of {len(results)}")

    await bot.close()


asyncio.run(run_all())
