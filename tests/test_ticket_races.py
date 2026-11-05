"""S15  Ticket automation races.

The ticket type select is a persistent view registered in `cog_load`, so a
double-click reached `open_ticket` twice concurrently. Both calls passed the
"user already has an open ticket" read and each created its own channel plus
its own `tickets` row.

`claim_ticket` had no guard either: two staff clicking Claim both succeeded and
the second silently overwrote the first.

These tests drive the real coroutines with a database double that yields
between its read and its write, which is what made the duplication reachable.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import discord
import pytest

from src.cogs.community.tickets import Tickets


class DB:
    """Yields between read and write so a missing lock becomes observable."""

    def __init__(self):
        self.config = {"guild_id": "5", "category_id": None, "staff_role_id": None,
                       "panel_channel_id": 10, "log_channel_id": None}
        self.rows = []
        self.concurrent_reads = 0
        self.max_concurrent_reads = 0

    async def fetch_one(self, table, filters):
        self.concurrent_reads += 1
        self.max_concurrent_reads = max(self.max_concurrent_reads, self.concurrent_reads)
        await asyncio.sleep(0)
        self.concurrent_reads -= 1
        if table == "ticket_config":
            return dict(self.config) if self.config else None
        if table == "tickets":
            for r in self.rows:
                if all(str(r.get(k)) == str(v) for k, v in filters.items()):
                    return dict(r)
        return None

    async def insert(self, table, data):
        await asyncio.sleep(0)
        data = dict(data)
        data["id"] = len(self.rows) + 1
        self.rows.append(data)

    async def update(self, table, filters, values):
        await asyncio.sleep(0)
        changed = []
        for r in self.rows:
            if all(str(r.get(k)) == str(v) for k, v in filters.items()):
                r.update(values)
                changed.append(dict(r))
        return changed


class _Sent:
    def __init__(self):
        self.count = 0

    async def send(self, **kw):
        self.count += 1


class Channel:
    _next = 1000

    def __init__(self):
        self.id = Channel._next
        Channel._next += 1
        self.name = "ticket"
        self.sent = _Sent()
        self.send = self.sent.send

    @property
    def mention(self):
        return f"<#{self.id}>"


class Guild:
    id = 5
    default_role = "everyone"
    me = "bot"

    def __init__(self):
        self.channels = []
        self.roles = {}
        self.name = "g"

    def get_channel(self, cid):
        return None

    def get_role(self, rid):
        return self.roles.get(rid)

    async def create_text_channel(self, name, category=None, overwrites=None, reason=None):
        await asyncio.sleep(0)
        ch = Channel()
        ch.name = name
        self.channels.append(ch)
        return ch


class Response:
    def __init__(self):
        self.replies = []
        self.deferred = False

    async def defer(self, **kw):
        self.deferred = True

    async def send_message(self, content=None, **kw):
        self.replies.append(content or "")

    send = send_message


class Interaction:
    """Minimal stand-in: `open_ticket` only needs .guild/.user/.response."""

    def __init__(self, guild, uid, staff_role=None):
        self.guild = guild
        self.guild_id = guild.id
        self.channel_id = 0
        self.user = _User(uid, staff_role)
        self.response = Response()
        self.followup = self.response


def _User(uid, staff_role=None):
    """discord.Member stand-in: the spec makes `isinstance` succeed."""
    user = MagicMock(spec=discord.Member)
    user.id = uid
    user.name = f"user{uid}"
    user.mention = f"<@{uid}>"
    user.roles = [staff_role] if staff_role is not None else []
    user.guild_permissions = SimpleNamespace(manage_channels=False)
    user.get_role.side_effect = lambda role_id: next(
        (r for r in user.roles if getattr(r, "id", None) == role_id), None
    )
    return user


def make_cog(db):
    bot = type("Bot", (), {"db_manager": db, "get_cog": lambda self, n: None})()
    return Tickets(bot)


# ══════════════ open_ticket: the critical section must be exclusive ══════════════

@pytest.mark.asyncio
async def test_duplicate_check_is_atomic_under_double_click():
    db = DB()
    cog = make_cog(db)
    guild = Guild()

    await asyncio.gather(
        cog.open_ticket(Interaction(guild, 7), "discord"),
        cog.open_ticket(Interaction(guild, 7), "discord"),
    )

    assert len(guild.channels) == 1, f"double click made {len(guild.channels)} channels"
    assert len(db.rows) == 1, f"double click wrote {len(db.rows)} rows"


@pytest.mark.asyncio
async def test_second_open_reports_the_existing_ticket():
    db = DB()
    cog = make_cog(db)
    guild = Guild()

    await cog.open_ticket(Interaction(guild, 7), "discord")
    second = Interaction(guild, 7)
    await cog.open_ticket(second, "discord")

    assert len(guild.channels) == 1
    assert any("нээлттэй ticket" in r for r in second.response.replies)


@pytest.mark.asyncio
async def test_two_members_open_independently():
    db = DB()
    cog = make_cog(db)
    guild = Guild()

    await asyncio.gather(
        cog.open_ticket(Interaction(guild, 1), "discord"),
        cog.open_ticket(Interaction(guild, 2), "rules"),
    )

    assert len(guild.channels) == 2, "one member must not block another"
    assert len(db.rows) == 2


@pytest.mark.asyncio
async def test_reads_never_overlap_for_the_same_member():
    db = DB()
    cog = make_cog(db)
    guild = Guild()

    await asyncio.gather(*(cog.open_ticket(Interaction(guild, 7), "discord") for _ in range(5)))

    assert db.max_concurrent_reads == 1, (
        f"the duplicate-check read ran {db.max_concurrent_reads}x concurrently"
    )


@pytest.mark.asyncio
async def test_lock_identity_is_per_guild_and_member():
    cog = make_cog(DB())
    assert cog._open_lock(5, 1) is cog._open_lock(5, 1)
    assert cog._open_lock(5, 1) is not cog._open_lock(5, 2)
    assert cog._open_lock(5, 1) is not cog._open_lock(6, 1)


@pytest.mark.asyncio
async def test_unconfigured_system_creates_nothing():
    db = DB()
    db.config = None
    cog = make_cog(db)
    guild = Guild()

    inter = Interaction(guild, 7)
    await cog.open_ticket(inter, "discord")

    assert guild.channels == []
    assert any("тохируулагдаагүй" in r for r in inter.response.replies)


# ══════════════ claim_ticket: first claimer wins ══════════════

@pytest.mark.asyncio
async def test_second_staff_member_cannot_steal_a_claim():
    db = DB()
    cog = make_cog(db)
    db.rows.append({"id": 1, "channel_id": 77, "opener_id": "7", "status": "open"})

    guild = Guild()
    role = SimpleNamespace(id=500)
    guild.roles = {500: role}
    db.config["staff_role_id"] = 500
    first = Interaction(guild, 100, staff_role=role)
    first.channel_id = 77
    await cog.claim_ticket(first)

    second = Interaction(guild, 200, staff_role=role)
    second.channel_id = 77
    await cog.claim_ticket(second)

    assert db.rows[0]["claimed_by"] == "100", "the first claimer must keep the ticket"
    assert any("claim хийсэн" in r for r in second.response.replies)


@pytest.mark.asyncio
async def test_repeated_claim_by_the_same_staff_is_idempotent():
    db = DB()
    cog = make_cog(db)
    db.rows.append({"id": 1, "channel_id": 78, "opener_id": "7", "status": "open"})

    guild = Guild()
    role = SimpleNamespace(id=500)
    guild.roles = {500: role}
    db.config["staff_role_id"] = 500
    for _ in range(3):
        inter = Interaction(guild, 100, staff_role=role)
        inter.channel_id = 78
        await cog.claim_ticket(inter)

    assert db.rows[0]["claimed_by"] == "100"


@pytest.mark.asyncio
async def test_non_staff_cannot_claim():
    db = DB()
    cog = make_cog(db)
    db.rows.append({"id": 1, "channel_id": 79, "opener_id": "7", "status": "open"})

    guild = Guild()   # no staff role configured, member lacks manage_channels
    inter = Interaction(guild, 300)
    inter.channel_id = 79
    await cog.claim_ticket(inter)

    assert "claimed_by" not in db.rows[0]
    assert any("эрхгүй" in r for r in inter.response.replies)


@pytest.mark.asyncio
async def test_claim_survives_restart_and_cannot_be_stolen():
    db = DB()
    db.config["staff_role_id"] = 500
    db.rows.append({"id": 1, "channel_id": 77, "opener_id": "7", "status": "open", "claimed_by": "100"})
    guild = Guild()
    role = SimpleNamespace(id=500)
    guild.roles = {500: role}
    inter = Interaction(guild, 200, staff_role=role)
    inter.channel_id = 77
    await make_cog(db).claim_ticket(inter)
    assert db.rows[0]["claimed_by"] == "100"
    assert any("claim хийсэн" in r for r in inter.response.replies)


@pytest.mark.asyncio
async def test_claim_is_atomic_across_independent_bot_workers():
    db = DB()
    db.config["staff_role_id"] = 500
    db.rows.append({"id": 1, "channel_id": 77, "opener_id": "7", "status": "open"})
    guild = Guild()
    role = SimpleNamespace(id=500)
    guild.roles = {500: role}
    interactions = [Interaction(guild, uid, staff_role=role) for uid in (100, 200)]
    for inter in interactions:
        inter.channel_id = 77
    await asyncio.gather(*(make_cog(db).claim_ticket(inter) for inter in interactions))
    assert db.rows[0]["claimed_by"] in ("100", "200")
    assert sum(any(r for r in inter.response.replies) for inter in interactions) == 1
    assert all(inter.response.deferred for inter in interactions)
