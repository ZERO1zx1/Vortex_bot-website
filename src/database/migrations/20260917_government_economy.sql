-- ============================================================================
-- AETHER: Government Economy System (2026-09-17)
-- ----------------------------------------------------------------------------
-- Adds the guild-specific Government Economy System:
--   * economy_guild_settings  - per-guild government/tax/treasury config
--   * government_members      - co-owner users (only the guild owner appoints)
--   * government_roles        - government roles stored by ROLE ID (not name)
--   * economy_jobs            - custom jobs used by /work and /economy
--   * tax_recipients          - configured tax distribution percentages
--   * economy_ledger          - audit trail for tax/treasury/job/role income
--
-- HOW TO RUN:
--   1. Supabase Dashboard -> SQL Editor -> paste THIS file -> Run.
--   2. Idempotent: safe to run multiple times, on any project.
--   3. Restart the bot afterwards (slash commands re-sync automatically).
--
-- The bot authenticates with service_role (bypasses RLS). Unconfigured
-- guilds keep the legacy economy behavior unchanged (existing tax + roles).
-- ============================================================================

-- Per-guild government / tax / treasury settings -----------------------------
CREATE TABLE IF NOT EXISTS economy_guild_settings (
    guild_id          TEXT PRIMARY KEY,
    government_enabled BOOLEAN  NOT NULL DEFAULT FALSE,
    tax_enabled       BOOLEAN  NOT NULL DEFAULT TRUE,
    tax_rate          NUMERIC  NOT NULL DEFAULT 10,
    treasury_balance  BIGINT   NOT NULL DEFAULT 0,
    treasury_public   BOOLEAN  NOT NULL DEFAULT FALSE,
    updated_at        BIGINT   DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

-- Government members (co-owners).  Only the guild owner may add/remove rows.
CREATE TABLE IF NOT EXISTS government_members (
    guild_id      TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    position      TEXT NOT NULL DEFAULT 'co_owner',
    appointed_by  TEXT,
    created_at    BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW())),
    PRIMARY KEY (guild_id, user_id, position)
);

-- Government roles stored as ROLE IDs (never names). role_type is one of:
--   government_admin | president | finance | tax_collector
CREATE TABLE IF NOT EXISTS government_roles (
    guild_id    TEXT NOT NULL,
    role_type   TEXT NOT NULL,
    role_id     BIGINT NOT NULL,
    updated_by  TEXT,
    updated_at  BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW())),
    PRIMARY KEY (guild_id, role_type)
);

-- Custom jobs for /work and the /economy jobs list.
CREATE TABLE IF NOT EXISTS economy_jobs (
    id               BIGSERIAL PRIMARY KEY,
    guild_id         TEXT NOT NULL,
    name             TEXT NOT NULL,
    emoji            TEXT NOT NULL DEFAULT '💼',
    required_level   INT  NOT NULL DEFAULT 0,
    required_role_id BIGINT,
    salary_min       BIGINT NOT NULL DEFAULT 1800,
    salary_max       BIGINT NOT NULL DEFAULT 5000,
    enabled          BOOLEAN NOT NULL DEFAULT TRUE,
    created_by       TEXT,
    created_at       BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW())),
    updated_at       BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

-- One job per (guild, name); names are unique, case-insensitive.
CREATE UNIQUE INDEX IF NOT EXISTS uq_economy_jobs_guild_name
    ON economy_jobs (LOWER(guild_id), LOWER(name));

-- Tax distribution recipients. recipient_type is one of:
--   treasury | owner | co_owner | user | role
-- recipient_key stores the user/role ID (0 for the non-ID types).
-- Percentages must sum to 100 before the config is activated.
CREATE TABLE IF NOT EXISTS tax_recipients (
    id             BIGSERIAL PRIMARY KEY,
    guild_id       TEXT NOT NULL,
    recipient_type TEXT NOT NULL,
    recipient_key  BIGINT NOT NULL DEFAULT 0,
    percentage     NUMERIC NOT NULL DEFAULT 0
                   CHECK (percentage >= 0 AND percentage <= 100),
    created_by     TEXT,
    created_at     BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW())),
    updated_at     BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tax_recipients_guild_type_key
    ON tax_recipients (guild_id, recipient_type, recipient_key);

-- Audit ledger.  Writes are best-effort: a ledger failure must never corrupt
-- the primary financial transaction (callers log and continue).
CREATE TABLE IF NOT EXISTS economy_ledger (
    id               BIGSERIAL PRIMARY KEY,
    guild_id         TEXT NOT NULL,
    user_id          TEXT,
    actor_id         TEXT,
    transaction_type TEXT NOT NULL,
    amount           BIGINT NOT NULL DEFAULT 0,
    treasury_before  BIGINT,
    treasury_after   BIGINT,
    balance_before   BIGINT,
    balance_after    BIGINT,
    reason           TEXT,
    metadata         TEXT,
    created_at       BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

CREATE INDEX IF NOT EXISTS ix_economy_ledger_guild_id
    ON economy_ledger (guild_id, created_at DESC);

-- ---------------------------------------------------------------------------
-- service_role grants (idempotent; mirrors the project's other migrations)
-- ---------------------------------------------------------------------------
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    economy_guild_settings,
    government_members,
    government_roles,
    economy_jobs,
    tax_recipients,
    economy_ledger
    TO service_role;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO service_role;

-- ---------------------------------------------------------------------------
-- Lock the new tables down (anon key cannot read/write them)
-- ---------------------------------------------------------------------------
ALTER TABLE economy_guild_settings  ENABLE ROW LEVEL SECURITY;
ALTER TABLE government_members       ENABLE ROW LEVEL SECURITY;
ALTER TABLE government_roles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE economy_jobs             ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_recipients           ENABLE ROW LEVEL SECURITY;
ALTER TABLE economy_ledger           ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE
    economy_guild_settings,
    government_members,
    government_roles,
    economy_jobs,
    tax_recipients,
    economy_ledger
    FROM anon, authenticated;

-- ---------------------------------------------------------------------------
-- Refresh PostgREST's schema cache so the new tables are available at once
-- ---------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';

-- Done.  Restart the bot; /government /economy-config /treasury /economy
-- will appear in the guild (owner must re-invite with the new scopes or
-- kick/refresh via the dashboard command list).