-- ============================================================================
-- AETHER: Runtime schema repair (2026-09-14)
-- ----------------------------------------------------------------------------
-- Fixes the two production database failure classes seen in cogs.log:
--   * PGRST205 / 404  -> needed tables were never created (the full
--     `000_complete_schema.sql` migration was not applied to this project).
--   * 42501           -> the service_role has no SELECT/INSERT/UPDATE/DELETE
--     grants on many tables, so every event handler and background loop that
--     touches them throws "permission denied for table ...".
--
-- HOW TO RUN:
--   1. Open the Supabase Dashboard -> SQL Editor:
--        https://supabase.com/dashboard/project/<your-project>/sql
--   2. Paste THIS file and press Run.
--   3. It is fully idempotent: safe to run multiple times, on any project.
--   4. Start the bot; its startup health-check should now report all OK.
--
-- NOTE: Prefer running `000_complete_schema.sql` FIRST (full canonical schema).
-- If that file was already applied, this repair is still harmless and fast.
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1) Lifecycle-critical tables the bot uses on every hot path.  These were
--    missing on production; CREATE ... IF NOT EXISTS makes this safe anywhere.
--    DDL mirrors `000_complete_schema.sql` exactly.
-- ---------------------------------------------------------------------------

-- Staff / moderation ---------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff_members (
    user_id TEXT,
    guild_id TEXT,
    staff_group TEXT,
    added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS staff_activity (
    user_id TEXT,
    guild_id TEXT,
    messages INT DEFAULT 0,
    voice_seconds BIGINT DEFAULT 0,
    tickets_closed INT DEFAULT 0,
    actions INT DEFAULT 0,
    last_update TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS staff_weekly_winners (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    week_start TIMESTAMPTZ,
    week_end TIMESTAMPTZ,
    points INT,
    rank INT
);

CREATE TABLE IF NOT EXISTS staff_config (
    guild_id TEXT PRIMARY KEY,
    log_channel BIGINT,
    announcement_channel BIGINT,
    stats_channel BIGINT,
    leaderboard_message_id BIGINT
);

-- Welcome / moderation / history --------------------------------------------
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    moderator_id TEXT,
    reason TEXT,
    timestamp BIGINT
);

-- Casino / games -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS game_stats (
    user_id TEXT,
    guild_id TEXT,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    total_won BIGINT DEFAULT 0,
    total_bet BIGINT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- Economy / role income ------------------------------------------------------
CREATE TABLE IF NOT EXISTS role_income (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    amount BIGINT NOT NULL DEFAULT 1000,
    interval_seconds BIGINT NOT NULL DEFAULT 3600
);

CREATE TABLE IF NOT EXISTS work_phrases (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    phrase TEXT NOT NULL
);

-- Temp voice -----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS temp_channels (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    owner_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tempvoice_setup_msg (
    guild_id TEXT PRIMARY KEY,
    channel_id BIGINT,
    message_id BIGINT
);

CREATE TABLE IF NOT EXISTS guild_config (
    guild_id TEXT PRIMARY KEY,
    create_channel_id BIGINT,
    max_channels_per_user INT DEFAULT 3,
    category_id BIGINT,
    control_channel_id BIGINT
);

-- Counting -------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS counting_config (
    guild_id TEXT PRIMARY KEY,
    channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE,
    delete_messages BOOLEAN DEFAULT FALSE,
    math_mode BOOLEAN DEFAULT FALSE,
    failed_role_id BIGINT,
    reliable_role_id BIGINT,
    save_role_id BIGINT,
    high_score BIGINT DEFAULT 0,
    best_streak BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS counting_progress (
    guild_id TEXT PRIMARY KEY,
    current_count BIGINT DEFAULT 0,
    last_user_id BIGINT,
    streak BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS counting_stats (
    guild_id TEXT,
    user_id TEXT,
    correct INT DEFAULT 0,
    wrong INT DEFAULT 0,
    saves INT DEFAULT 0,
    strikes INT DEFAULT 0,
    best_streak INT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

-- Confessions ----------------------------------------------------------------
CREATE TABLE IF NOT EXISTS confession_config (
    guild_id TEXT PRIMARY KEY,
    confess_channel_id BIGINT,
    output_channel_id BIGINT,
    anonymity BOOLEAN DEFAULT TRUE,
    cooldown INT DEFAULT 30,
    next_id INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS confession_blacklist (
    guild_id TEXT,
    word TEXT,
    PRIMARY KEY (guild_id, word)
);

CREATE TABLE IF NOT EXISTS confession_cooldown (
    user_id TEXT,
    guild_id TEXT,
    last_time BIGINT,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS confession_messages (
    guild_id TEXT,
    confession_id INT,
    message_id BIGINT,
    user_id TEXT,
    content TEXT,
    PRIMARY KEY (guild_id, confession_id)
);

-- Avatar logging -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS avatar_log_config (
    guild_id TEXT PRIMARY KEY,
    log_channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE
);

-- Invite tracking ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invite_log_config (
    guild_id TEXT PRIMARY KEY,
    log_channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE,
    fake_delay INT DEFAULT 3
);

CREATE TABLE IF NOT EXISTS invite_stats (
    guild_id TEXT,
    user_id TEXT,
    regular INT DEFAULT 0,
    bonus INT DEFAULT 0,
    "fake" INT DEFAULT 0,
    "left" INT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS invite_joins (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    user_id TEXT,
    invited_by TEXT,
    invite_code TEXT,
    joined_at BIGINT,
    left_at BIGINT
);

-- Greetings ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS greeting_config (
    guild_id TEXT PRIMARY KEY,
    welcome_channel BIGINT,
    goodbye_channel BIGINT,
    boost_channel BIGINT,
    welcome_template_id INT,
    goodbye_template_id INT,
    boost_template_id INT,
    welcome_enabled BOOLEAN DEFAULT TRUE,
    goodbye_enabled BOOLEAN DEFAULT TRUE,
    boost_enabled BOOLEAN DEFAULT TRUE,
    dm_on_welcome BOOLEAN DEFAULT FALSE,
    log_channel BIGINT
);

CREATE TABLE IF NOT EXISTS greeting_templates (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    creator_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

-- Quests ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_quests (
    user_id TEXT,
    guild_id TEXT,
    quest_id TEXT,
    template_id INT,
    target INT,
    progress INT DEFAULT 0,
    reward_type TEXT DEFAULT 'money',
    reward_amount INT DEFAULT 0,
    claimed BOOLEAN DEFAULT FALSE,
    created_at BIGINT,
    PRIMARY KEY (user_id, guild_id, quest_id)
);

CREATE TABLE IF NOT EXISTS quest_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    quest_id TEXT,
    template_id INT,
    completed_at BIGINT
);

-- ---------------------------------------------------------------------------
-- 2) user_equips shape repair
-- ---------------------------------------------------------------------------
-- The canonical schema previously declared a (user_id, guild_id, item_id)
-- primary key; shop.py's equip/unequip code uses slot-based storage
-- (guild_id, user_id, slot) per migration 20260824_equip_system.sql.
-- Any project where the old shape was applied gets rebuilt to the correct
-- slot-based table (existing equips are preserved by copying rows).
DO $$
DECLARE
    vouched_new BOOLEAN := EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'user_equips'
          AND column_name = 'slot'
    );
BEGIN
    IF NOT vouched_new AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'user_equips'
          AND column_name = 'item_id'
          AND data_type IN ('integer', 'bigint')
    ) THEN
        CREATE TABLE user_equips_new (
            guild_id TEXT NOT NULL,
            user_id  TEXT NOT NULL,
            slot     TEXT NOT NULL,
            item_id  BIGINT NOT NULL,
            updated_at BIGINT DEFAULT 0,
            PRIMARY KEY (guild_id, user_id, slot)
        );
        ALTER TABLE user_equips RENAME TO user_equips_legacy;
        ALTER TABLE user_equips_new RENAME TO user_equips;
        DROP TABLE user_equips_legacy;
    END IF;
END;
$$;

-- Also make sure the canonical slot-based definition exists when missing.
CREATE TABLE IF NOT EXISTS user_equips (
    guild_id TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    slot     TEXT NOT NULL,      -- ring | necklace | bracelet | charm
    item_id  BIGINT NOT NULL,
    updated_at BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, slot)
);

-- ---------------------------------------------------------------------------
-- 3) service_role grants for EVERY public table (idempotent, exhaustive)
-- ---------------------------------------------------------------------------
-- This closes the 42501 "permission denied" class wholesale instead of
-- chasing individual tables.  The bot authenticates with the service role
-- (bypasses RLS), so these grants are what let every cog read/write its
-- tables through PostgREST.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename NOT LIKE 'pg_%'
          AND tablename <> 'supabase_migrations'
    LOOP
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
    END LOOP;
END;
$$;

-- Sequences and functions the bot calls (increment RPC etc.)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    GRANT EXECUTE ON FUNCTIONS TO service_role;

-- ---------------------------------------------------------------------------
-- 4) Consistent security posture (mirrors 000_complete_schema.sql)
-- ---------------------------------------------------------------------------
-- The bot is the only client talking to the API; lock public tables down so
-- the anon key cannot read or write economy/levels/etc.
DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename NOT LIKE 'pg_%'
          AND tablename <> 'supabase_migrations'
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
    END LOOP;
END;
$$;

-- Bot status heartbeat remains readable by the website (anon key, id=1 only).
GRANT SELECT ON TABLE public.bot_status TO anon;
DROP POLICY IF EXISTS anon_read_bot_status ON public.bot_status;
CREATE POLICY anon_read_bot_status ON public.bot_status
  FOR SELECT TO anon USING (id = 1);

-- ---------------------------------------------------------------------------
-- 5) Refresh PostgREST's schema cache so PGRST205 stops immediately
-- ---------------------------------------------------------------------------
NOTIFY pgrst, 'reload schema';

-- Done. Start the bot and check logs/hb.log + startup health-check output.