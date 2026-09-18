"""Tests for the Government Economy System (cogs/government.py + integration).

26 scenarios covering:
  1-4   pure helpers (parse, compute_tax, allocate_dividend, recipient sets)
  5-7   guild settings + government status/tax mode
  8-11  tax recipients (cap, upsert, below-100 -> treasury fallback, cleanup)
  12-15 custom jobs (duplicate rejection, create/resolve, role gate, CRUD)
  16-17 role income (interval bounds, upsert)
  18-20 treasury (credit, split pay + ledger, insufficient funds)
  21-22 co-owners + permissions hierarchy
  23-25 tax distribution (unconfigured fallback, configured recipients,
          no recursive tax)
  26    economy.update_balance routes tax through the government when active

Unconfigured guilds must keep the legacy economy behavior (government_tax
returns None -> economy falls back to its legacy transfer_tax_percent).
"""
from types import SimpleNamespace

import pytest

import src.cogs.government as gov_mod
from src.cogs.economy import Economy
from src.cogs.government import Government


# ══════════════ FAKES ══════════════

class FakeGuild:
    def __init__(self, gid, owner_id, name="Test Guild"):
        self.id = int(gid)
        self.owner_id = int(owner_id)
        self.name = name
        self.roles = {}
        self.members = {}

    def add_role(self, role):
        self.roles[int(role.id)] = role
        return self

    def add_member(self, member):
        self.members[int(member.id)] = member
        return self

    def get_role(self, rid):
        return self.roles.get(int(rid))

    def get_member(self, uid):
        return self.members.get(int(uid))


class FakeRole:
    def __init__(self, rid, name="Role", members=None):
        self.id = int(rid)
        self.name = name
        self.members = list(members or [])

    def __repr__(self):
        return f"<FakeRole {self.id} {self.name!r}>"


class FakeMember:
    def __init__(self, uid, roles=None, bot=False):
        self.id = int(uid)
        self.roles = list(roles or [])
        self.bot = bot

    def __repr__(self):
        return f"<FakeMember {self.id}>"


class FakeDB:
    """Tiny in-memory stand-in for SupabaseManager (fetch/update/insert)."""

    def __init__(self):
        self.tables = {}

    def _rows(self, table):
        return self.tables.setdefault(table, [])

    @staticmethod
    def _match(row, query):
        return all(str(row.get(k)) == str(v) for k, v in query.items())

    async def fetch_one(self, table, query, selects=None):
        for row in self._rows(table):
            if self._match(row, query):
                if selects:
                    return {selects: row.get(selects)}
                return dict(row)
        return None

    async def fetchone(self, table, query):
        return await self.fetch_one(table, query)

    async def fetchall(self, table, query=None):
        if query is None:
            return [dict(r) for r in self._rows(table)]
        return [dict(r) for r in self._rows(table) if self._match(r, query)]

    async def fetch_all(self, table, query=None, order_by=None, desc=False,
                        limit=None, offset=None):
        rows = await self.fetchall(table, query)
        if offset:
            rows = rows[offset:]
        if limit:
            rows = rows[:limit]
        return rows

    async def delete(self, table, query):
        rows = self._rows(table)
        rows[:] = [r for r in rows if not self._match(r, query)]

    async def insert(self, table, data):
        self._rows(table).append(dict(data))

    async def execute(self, table, data):
        query = {"user_id": data.get("user_id"), "guild_id": data.get("guild_id")}
        return await self.update(table, query, data) or self._rows(table).append(dict(data))

    async def update(self, table, query, data):
        for row in self._rows(table):
            if self._match(row, query):
                row.update(dict(data))
                return True
        return False

    async def upsert(self, table, data, on_conflict=None):
        query = {on_conflict: data.get(on_conflict)} if on_conflict else {
            "user_id": data.get("user_id"), "guild_id": data.get("guild_id"),
        }
        for row in self._rows(table):
            if self._match(row, query):
                row.update(dict(data))
                return
        self._rows(table).append(dict(data))


class GovFakeDB(FakeDB):
    """Like FakeDB, but matches the real SupabaseManager surface the gov cog
    relies on: optional query + selects/order_by/desc in fetch_safe, and
    auto-assigned row ids for tables whose primary keys are generated server
    side (economy_jobs, economy_ledger, tax_recipients, ...)."""

    def __init__(self):
        super().__init__()
        self._seq = {}

    def _next_id(self, table):
        self._seq[table] = self._seq.get(table, 0) + 1
        return self._seq[table]

    async def fetch_safe(self, table, query=None, single=False, selects=None,
                         order_by=None, desc=False):
        rows = await self.fetch_all(table, query, order_by=order_by, desc=desc)
        if single:
            if not rows:
                return None
            row = rows[0]
            if selects:
                return {selects: row.get(selects)}
            return dict(row)
        if selects:
            keys = [k.strip() for k in selects.split(",")]
            return [{k: r.get(k) for k in keys} for r in rows]
        return rows

    async def fetchall(self, table, query=None):
        rows = super()._rows(table)
        if query is None:
            return [dict(r) for r in rows]
        return [dict(r) for r in rows if FakeDB._match(r, query)]

    def preload(self, table, rows):
        self.tables.setdefault(table, []).extend(list(rows))


class GovFakeBot:
    def __init__(self, config=None, db=None, guilds=None):
        self.config = config or {}
        self.db_manager = db or GovFakeDB()
        self._cogs = {}
        self.loop = None  # Economy background loops only start in cog_load()
        self._guilds = guilds or {}

    def add_cog(self, name, cog):
        self._cogs[name] = cog

    def get_cog(self, name):
        return self._cogs.get(name)

    def get_guild(self, gid):
        return self._guilds.get(int(gid))


# ══════════════ HELPERS ══════════════

def make_gov(db, guild, config=None):
    bot = GovFakeBot(config=config or {"tax_percent": 10, "max_balance": 1_000_000}, db=db)
    bot._guilds[int(guild.id)] = guild
    gov = Government(bot)
    bot.add_cog("Government", gov)
    return bot, gov


def make_econ(bot):
    eco = Economy(bot)
    bot.add_cog("Economy", eco)
    return eco


def user_interaction(guild, uid, roles=None, owner=False):
    return SimpleNamespace(guild=guild, user=FakeMember(uid, roles=roles or [], bot=False))


# ══════════════ 1-4: PURE HELPERS ══════════════

def test_parse_helpers_bounds():
    assert gov_mod.parse_pct("75") == 75
    assert gov_mod.parse_pct("-1") is None
    assert gov_mod.parse_pct("101") is None
    assert gov_mod.parse_pct("abc") is None
    assert gov_mod.parse_money("5000", maximum=1_000_000) == 5000
    assert gov_mod.parse_money("5001", maximum=5000) is None
    assert gov_mod.parse_money("-3") is None
    assert gov_mod.parse_level("12") == 12
    assert gov_mod.parse_level("-1") is None
    assert gov_mod.parse_role_ref("<@&123>") == 123
    assert gov_mod.parse_role_ref("123") == 123
    assert gov_mod.parse_role_ref("-") is None
    assert gov_mod.parse_role_ref("0") is None


def test_compute_tax_floors_and_clamps_rate():
    assert gov_mod.compute_tax(1000, 15) == (150, 850)
    assert gov_mod.compute_tax(1000, 200) == (1000, 0)  # rate clamped to 100 -> full tax
    assert gov_mod.compute_tax(-5, 10) == (0, -5)
    assert gov_mod.compute_tax(1000, 0) == (0, 1000)


def test_allocate_dividend_remainder_to_first():
    assert gov_mod.allocate_dividend(10, 3) == [4, 3, 3]
    assert gov_mod.allocate_dividend(7, 2) == [4, 3]
    assert gov_mod.allocate_dividend(10, 0) == []
    assert gov_mod.allocate_dividend(0, 3) == [0, 0, 0]


def test_validate_recipient_set_requires_exact_100():
    ok, total, _msg = gov_mod.validate_recipient_set([
        {"percentage": 60},
        {"percentage": 20},
    ])
    assert not ok and total == 80
    ok, total, _msg = gov_mod.validate_recipient_set(  # never more than 100
        [{"percentage": 60}, {"percentage": 50}]
    )
    assert not ok and total == 110
    ok, total, _msg = gov_mod.validate_recipient_set(
        [{"percentage": 60}, {"percentage": 40}]
    )
    assert ok and total == 100


# ══════════════ 5-7: SETTINGS / STATUS / TAX MODE ══════════════

@pytest.mark.asyncio
async def test_settings_defaults_and_upsert_single_row():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    s = await gov.get_settings(5)
    assert s["government_enabled"] is False
    assert s["tax_rate"] == gov_mod.DEFAULT_TAX_RATE
    assert s["tax_enabled"] is True
    assert s["treasury_balance"] == 0

    await gov._save_settings(5, tax_rate=25, government_enabled=True)
    await gov._save_settings(5, tax_rate=30)
    assert await gov.get_settings(5) == {
        "guild_id": "5",
        "government_enabled": True,
        "tax_enabled": True,
        "tax_rate": 30,
        "treasury_balance": 0,
        "treasury_public": False,
        "updated_at": db.tables[gov_mod.SETTINGS_TABLE][0]["updated_at"],
    }
    assert len(db.tables[gov_mod.SETTINGS_TABLE]) == 1  # upsert, not insert


@pytest.mark.asyncio
async def test_government_tax_none_when_inactive_legacy_applies():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    assert await gov.is_government_active(5) is False
    assert await gov.government_tax(5) is None  # -> economy keeps legacy rate


@pytest.mark.asyncio
async def test_government_tax_active_rate_and_enabled_flag():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    await gov._save_settings(5, government_enabled=True, tax_rate=7, tax_enabled=False)
    rate, enabled = await gov.government_tax(5)
    assert rate == 7 and enabled is False
    await gov._save_settings(5, tax_enabled=True, tax_rate=101)  # clamp to 100
    rate, enabled = await gov.government_tax(5)
    assert rate == 100 and enabled is True


# ══════════════ 8-11: TAX RECIPIENTS ══════════════

@pytest.mark.asyncio
async def test_set_recipient_cap_and_over_100_rejection():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    ok, msg = await gov.set_recipient(5, "treasury", 0, 60, created_by="1")
    assert ok and "100%" in msg and "идэвхэжи" not in msg
    ok, msg = await gov.set_recipient(5, "owner", 0, 50, created_by="1")
    assert not ok and "100%" in msg  # 60 + 50 > 100 rejected
    ok, _msg = await gov.set_recipient(5, "treasury", 0, 100, created_by="1")
    assert ok
    assert gov_mod.recipient_total(await gov.get_recipients(5)) == 100


@pytest.mark.asyncio
async def test_set_recipient_upserts_same_user_and_activates_at_100():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    _bot, gov = make_gov(db, guild)
    ok, msg = await gov.set_recipient(5, "user", 42, 80, created_by="1")
    assert ok and "80%" in msg
    ok, msg = await gov.set_recipient(5, "user", 42, 100, created_by="1")
    assert ok and "идэвхэл" in msg.lower()
    rows = db.tables[gov_mod.RECIPIENTS_TABLE]
    assert len(rows) == 1  # same (type, key) updated, not duplicated
    assert int(rows[0]["percentage"]) == 100


@pytest.mark.asyncio
async def test_recipients_below_100_fallback_to_treasury():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    bot, gov = make_gov(db, guild)
    eco = make_econ(bot)
    await gov._save_settings(5, government_enabled=True)  # rate irrelevant here
    db.preload("economy", [{"user_id": "42", "guild_id": "5", "balance": 0}])
    await gov.set_recipient(5, "user", 42, 40, created_by="1")  # total only 40%
    assert await gov.distribute_tax(5, 1000) == 0
    assert await gov.get_treasury_balance(5) == 1000  # full fallback, no partial
    assert await eco.get_balance(42, 5) == 0


@pytest.mark.asyncio
async def test_remove_and_clear_recipients():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    await gov.set_recipient(5, "treasury", 0, 50, created_by="1")
    await gov.set_recipient(5, "user", 42, 50, created_by="1")
    assert len(db.tables[gov_mod.RECIPIENTS_TABLE]) == 2
    await gov.remove_recipient(5, "user", 42)
    assert len(await gov.get_recipients(5)) == 1
    await gov.clear_recipients(5)
    assert await gov.get_recipients(5) == []


# ══════════════ 12-15: CUSTOM JOBS ══════════════

@pytest.mark.asyncio
async def test_create_job_rejects_duplicate_name():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    ok, _msg = await gov.create_job(5, {
        "name": "Такси", "emoji": "🚕",
        "required_level": 0, "salary_min": 500, "salary_max": 1500,
    }, created_by="1")
    assert ok
    ok, msg = await gov.create_job(5, {
        "name": "такси", "emoji": "🚕",
        "required_level": 0, "salary_min": 500, "salary_max": 1500,
    }, created_by="1")
    assert not ok and "аль хэдийн байна" in msg
    assert len(db.tables[gov_mod.JOBS_TABLE]) == 1


@pytest.mark.asyncio
async def test_create_job_and_resolve_best_level():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    _bot, gov = make_gov(db, guild)
    await gov.create_job(5, {
        "name": "Зар сурталчилгаа",
        "required_level": 0, "salary_min": 100, "salary_max": 200,
    }, created_by="1")
    await gov.create_job(5, {
        "name": "Программист",
        "required_level": 5, "salary_min": 2000, "salary_max": 4000,
    }, created_by="1")
    job = await gov.resolve_user_job(5, level=7, member=FakeMember(42))
    assert job["name"] == "Программист"  # highest qualifying level
    job_low = await gov.resolve_user_job(5, level=2, member=FakeMember(42))
    assert job_low["name"] == "Зар сурталчилгаа"
    assert (await gov.resolve_user_job(5, level=0, member=FakeMember(42)))["name"] == "Зар сурталчилгаа"


@pytest.mark.asyncio
async def test_resolve_user_job_respects_role_gate():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42)).add_member(FakeMember(43))
    _bot, gov = make_gov(db, guild)
    await gov.create_job(5, {
        "name": "Нээлттэй ажил", "required_level": 0,
        "salary_min": 100, "salary_max": 200,
    }, created_by="1")
    await gov.create_job(5, {
        "name": "Хаалттай ажил", "required_level": 0, "required_role_id": 999,
        "salary_min": 500, "salary_max": 900,
    }, created_by="1")
    plain = await gov.resolve_user_job(5, level=0, member=FakeMember(42))
    assert plain["name"] == "Нээлттэй ажил"  # no role 999 -> gated job skipped
    insider = FakeMember(43, roles=[FakeRole(999, "VIP")])
    privileged = await gov.resolve_user_job(5, level=0, member=insider)
    assert privileged["name"] == "Хаалттай ажил"  # higher salary wins when eligible


@pytest.mark.asyncio
async def test_update_toggle_delete_job():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    _bot, gov = make_gov(db, guild)
    await gov.create_job(5, {
        "name": "Ажил", "required_level": 0, "salary_min": 100, "salary_max": 200,
    }, created_by="1")
    jid = (await gov.get_custom_jobs(5))[0]["id"]
    ok, _msg = await gov.update_job(5, jid, name="Шинэ ажил", salary_max=300)
    assert ok
    job = await gov.get_job(5, jid)
    assert job["name"] == "Шинэ ажил" and job["salary_max"] == 300
    ok, _msg = await gov.toggle_job_enabled(5, jid)
    assert ok and (await gov.get_job(5, jid))["enabled"] is False
    assert await gov.resolve_user_job(5, level=5, member=FakeMember(42)) is None
    ok, _msg = await gov.delete_job(5, jid)
    assert ok and await gov.get_job(5, jid) is None


# ══════════════ 16-17: ROLE INCOME ══════════════

@pytest.mark.asyncio
async def test_role_income_interval_bounds_rejected():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    ok, _msg = await gov.set_role_income(5, 55, 100, 1800, changed_by="1")
    assert not ok  # below MIN_ROLE_INCOME_INTERVAL (1h spam guard)
    ok, _msg = await gov.set_role_income(5, 55, 100, 7 * 24 * 3600 + 1, changed_by="1")
    assert not ok
    ok, _msg = await gov.set_role_income(5, 55, 0, 7200, changed_by="1")
    assert not ok
    ok, _msg = await gov.set_role_income(5, 55, 100, 7200, changed_by="1")
    assert ok


@pytest.mark.asyncio
async def test_role_income_upsert_and_remove():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    await gov.set_role_income(5, 55, 100, 7200, changed_by="1")
    await gov.set_role_income(5, 55, 250, 14400, changed_by="1")  # update, not dup
    assert len(db.tables[gov_mod.ROLE_INCOME_TABLE]) == 1
    incomes = await gov.get_role_incomes(5)
    inc = gov.get_role_income(incomes, 55)
    assert inc["amount"] == 250 and inc["interval_seconds"] == 14400
    await gov.remove_role_income(5, 55)
    assert await gov.get_role_incomes(5) == []


# ══════════════ 18-20: TREASURY ══════════════

@pytest.mark.asyncio
async def test_credit_treasury_and_balance():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    assert await gov.credit_treasury(5, 0, reason="noop") is False
    assert await gov.credit_treasury(5, 250, reason="seed") is True
    assert await gov.get_treasury_balance(5) == 250
    ledger = await gov.get_ledger(5)
    assert any(r["transaction_type"] == "treasury_deposit" and r["amount"] == 250
               for r in ledger)


@pytest.mark.asyncio
async def test_treasury_pay_split_and_ledger():
    db = GovFakeDB()
    guild = (FakeGuild(5, 1)
             .add_member(FakeMember(10)).add_member(FakeMember(11)).add_member(FakeMember(12)))
    bot, gov = make_gov(db, guild)
    eco = make_econ(bot)
    db.preload("economy", [
        {"user_id": "10", "guild_id": "5", "balance": 0},
        {"user_id": "11", "guild_id": "5", "balance": 0},
        {"user_id": "12", "guild_id": "5", "balance": 0},
    ])
    await gov.credit_treasury(5, 300, reason="seed")
    ok, _msg = await gov.treasury_pay(5, [10, 11, 12], 100, reason="bonus", actor_id="1")
    assert ok
    assert await gov.get_treasury_balance(5) == 200
    assert await eco.get_balance(10, 5) == 34  # remainder to first
    assert await eco.get_balance(11, 5) == 33
    assert await eco.get_balance(12, 5) == 33
    ledger = await gov.get_ledger(5)
    types = [r["transaction_type"] for r in ledger]
    assert types.count("treasury_payment") == 1
    assert types.count("treasury_payout") == 3


@pytest.mark.asyncio
async def test_treasury_pay_rejects_insufficient_funds():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    await gov.credit_treasury(5, 50, reason="seed")
    ok, msg = await gov.treasury_pay(5, [10, 11], 100, reason="too big", actor_id="1")
    assert not ok and "хүрэлцэхүйц" in msg
    assert await gov.get_treasury_balance(5) == 50  # untouched


# ══════════════ 21-22: CO-OWNERS + PERMISSIONS ══════════════

@pytest.mark.asyncio
async def test_co_owner_add_remove_duplicate():
    db = GovFakeDB()
    _bot, gov = make_gov(db, FakeGuild(5, 1))
    ok, _msg = await gov.add_co_owner(5, 9, appointed_by="1")
    assert ok and await gov.is_co_owner_id(5, 9)
    assert await gov.get_co_owner_ids(5) == [9]
    ok, msg = await gov.add_co_owner(5, 9, appointed_by="1")
    assert not ok and "аль хэдийн" in msg
    ok, _msg = await gov.remove_co_owner(5, 9)
    assert ok and not await gov.is_co_owner_id(5, 9)
    ok, _msg = await gov.remove_co_owner(5, 9)
    assert not ok  # already gone


@pytest.mark.asyncio
async def test_permissions_hierarchy():
    db = GovFakeDB()
    guild = FakeGuild(5, 1)
    _bot, gov = make_gov(db, guild)
    finance_role = FakeRole(500, "Finance")
    collector_role = FakeRole(501, "TaxCollector")
    president_role = FakeRole(502, "President")
    await gov.set_government_role(5, "finance", 500, updated_by="1")
    await gov.set_government_role(5, "tax_collector", 501, updated_by="1")
    await gov.set_government_role(5, "president", 502, updated_by="1")

    owner = await gov.compute_perms(user_interaction(guild, guild.owner_id))
    assert owner.owner and owner.government and owner.economy and owner.treasury_manage

    finance = await gov.compute_perms(user_interaction(guild, 21, roles=[finance_role]))
    assert finance.government is False
    assert finance.economy is True
    assert finance.treasury_manage is True

    collector = await gov.compute_perms(
        user_interaction(guild, 22, roles=[collector_role])
    )
    assert collector.economy is False
    assert collector.treasury_manage is False
    assert collector.treasury_ro is True  # read-only treasury

    president = await gov.compute_perms(
        user_interaction(guild, 23, roles=[president_role])
    )
    assert president.government is True and president.economy is True

    nobody = await gov.compute_perms(user_interaction(guild, 24))
    assert not (nobody.owner or nobody.government or nobody.economy
                or nobody.treasury_ro or nobody.treasury_manage)


# ══════════════ 23-25: TAX DISTRIBUTION ══════════════

@pytest.mark.asyncio
async def test_distribute_tax_unconfigured_fallbacks_to_treasury():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    bot, gov = make_gov(db, guild)
    make_econ(bot)
    await gov._save_settings(5, government_enabled=True)
    assert await gov.distribute_tax(5, 500) == 0  # no recipients yet
    assert await gov.get_treasury_balance(5) == 500
    assert len(db.tables.get(gov_mod.LEDGER_TABLE, [])) > 0  # fallback logged


@pytest.mark.asyncio
async def test_distribute_tax_credits_configured_recipients():
    db = GovFakeDB()
    guild = (FakeGuild(5, 1)
             .add_member(FakeMember(42)).add_member(FakeMember(43)))
    bot, gov = make_gov(db, guild)
    eco = make_econ(bot)
    await gov._save_settings(5, government_enabled=True)
    db.preload("economy", [
        {"user_id": "42", "guild_id": "5", "balance": 0},
        {"user_id": "43", "guild_id": "5", "balance": 0},
    ])
    await gov.set_recipient(5, "user", 42, 60, created_by="1")
    await gov.set_recipient(5, "user", 43, 40, created_by="1")
    distributed = await gov.distribute_tax(5, 1000)
    assert distributed == 1000
    assert await eco.get_balance(42, 5) == 600
    assert await eco.get_balance(43, 5) == 400
    assert await gov.get_treasury_balance(5) == 0  # nothing left over


@pytest.mark.asyncio
async def test_distribute_tax_no_recursive_tax():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(42))
    bot, gov = make_gov(db, guild)
    eco = make_econ(bot)
    await gov._save_settings(5, government_enabled=True, tax_rate=10)
    db.preload("economy", [{"user_id": "42", "guild_id": "5", "balance": 0}])
    await gov.set_recipient(5, "user", 42, 100, created_by="1")
    await gov.distribute_tax(5, 1000)
    assert await eco.get_balance(42, 5) == 1000  # apply_tax=False, exact amount
    assert await gov.get_treasury_balance(5) == 0


# ══════════════ 26: ECONOMY INTEGRATION (ROUTING) ══════════════

@pytest.mark.asyncio
async def test_economy_update_balance_routes_tax_through_government_when_active():
    db = GovFakeDB()
    guild = FakeGuild(5, 1).add_member(FakeMember(7))
    bot, gov = make_gov(db, guild)
    eco = make_econ(bot)
    db.preload("economy", [{"user_id": "7", "guild_id": "5", "balance": 1000}])

    # Legacy path first: government inactive -> legacy 10% tax, no treasury.
    assert await eco.update_balance(7, 5, 100) == 1090
    assert await gov.get_treasury_balance(5) == 0

    # Active government with treasury-only recipients: tax goes to treasury.
    await gov._save_settings(5, government_enabled=True, tax_rate=10, tax_enabled=True)
    await gov.set_recipient(5, "treasury", 0, 100, created_by="1")
    eco.invalidate_tax_cache(5)  # force a fresh tax-mode read
    assert await eco.update_balance(7, 5, 100) == 1180  # 1090 + 90 credited
    assert await gov.get_treasury_balance(5) == 10
    assert eco._tax_collected.get(5, 0) == 20  # 10 legacy (inactive) + 10 gov

    # Disabled tax -> no taxation at all.
    await gov._save_settings(5, tax_enabled=False)
    eco.invalidate_tax_cache(5)
    assert await eco.update_balance(7, 5, 100) == 1280
    assert await gov.get_treasury_balance(5) == 10