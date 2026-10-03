-- ========================================================================
-- AETHER full-schema bootstrap: run this ENTIRE file once in the Supabase
-- Dashboard SQL Editor for a fresh/empty test project.
--   https://supabase.com/dashboard/project/zwpgweaikpjkftkzmlak/sql
-- Every section is idempotent (IF NOT EXISTS / OR REPLACE / DO block), so
-- re-running any part is safe.
-- Ordered chronologically; grants and RLS applied last.
-- ========================================================================

-- ============ BEGIN: 000_complete_schema.sql ============
-- =============================================================
-- Migration: 000_complete_schema.sql
-- Bot: 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹
-- Purpose: Complete non-destructive schema for the live Supabase project.
--          This consolidated file includes every table, index, and the
--          atomic increment function required by the bot — it is the ONLY
--          migration file that needs to be run in the SQL Editor.
--          (automod_config, reaction_roles, bot_status and the
--          guild_config.lang column are included here as well.)
--
-- This migration is NON-DESTRUCTIVE: every statement uses
--   CREATE TABLE IF NOT EXISTS,
--   CREATE INDEX IF NOT EXISTS,
--   CREATE OR REPLACE FUNCTION.
-- No DROP / TRUNCATE / DELETE is executed.
-- =============================================================

-- ── Economy ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS economy (
    user_id TEXT,
    guild_id TEXT,
    balance BIGINT DEFAULT 1000,
    bank_balance BIGINT DEFAULT 0,
    last_daily BIGINT,
    last_work BIGINT,
    bank_protect_until BIGINT DEFAULT 0,
    prison_until BIGINT DEFAULT 0,
    hunger INT DEFAULT 0,
    mood INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Levels ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS levels (
    user_id TEXT,
    guild_id TEXT,
    xp BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    message_count INT DEFAULT 0,
    voice_seconds BIGINT DEFAULT 0,
    reaction_count INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS leveling_config (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    announce_channel BIGINT,
    voice_xp_enabled BOOLEAN DEFAULT TRUE,
    prog_type TEXT DEFAULT 'arithmetic',
    prog_base INT DEFAULT 100,
    prog_step FLOAT DEFAULT 150,
    xp_tiers TEXT,
    xp_media INT DEFAULT 15,
    xp_reaction INT DEFAULT 1,
    xp_voice_silent INT DEFAULT 5,
    xp_voice_talking INT DEFAULT 15,
    msg_cooldown INT DEFAULT 60,
    react_cooldown INT DEFAULT 10,
    background_url TEXT,
    font_name TEXT,
    xp_drop_enabled BOOLEAN DEFAULT FALSE,
    xp_drop_channel BIGINT,
    xp_drop_min INT DEFAULT 100,
    xp_drop_max INT DEFAULT 500,
    xp_drop_interval INT DEFAULT 3600,
    cafe_buff_enabled BOOLEAN DEFAULT TRUE,
    invite_xp INT DEFAULT 0,
    marriage_bonus FLOAT DEFAULT 0.1
);

CREATE TABLE IF NOT EXISTS level_roles (
    guild_id TEXT,
    level INT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS level_rewards (
    guild_id TEXT,
    level INT,
    money INT DEFAULT 0,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS leveling_exceptions (
    guild_id TEXT,
    type TEXT,
    target_id TEXT,
    PRIMARY KEY (guild_id, type, target_id)
);

-- ── Warnings ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    moderator_id TEXT,
    reason TEXT,
    timestamp BIGINT
);

-- ── Marriages ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS marriages (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    partner_id TEXT,
    guild_id TEXT,
    marriage_date TEXT,
    ring_name TEXT,
    ring_emoji TEXT,
    love_points INT DEFAULT 0,
    UNIQUE (user_id, partner_id, guild_id)
);

CREATE TABLE IF NOT EXISTS marriage_proposals (
    guild_id TEXT,
    from_id TEXT,
    to_id TEXT,
    proposal_type TEXT,
    ring_id INT DEFAULT 0,
    expires_at BIGINT,
    PRIMARY KEY (guild_id, from_id, to_id, proposal_type)
);

CREATE TABLE IF NOT EXISTS adoptions (
    guild_id TEXT,
    parent_id TEXT,
    child_id TEXT,
    type TEXT DEFAULT 'adoption',
    adopted_since BIGINT,
    PRIMARY KEY (guild_id, parent_id, child_id)
);

CREATE TABLE IF NOT EXISTS marriage_user_settings (
    guild_id TEXT,
    user_id TEXT,
    blocked BOOLEAN DEFAULT FALSE,
    auto_accept_marriage BOOLEAN DEFAULT FALSE,
    last_gift_daily BIGINT DEFAULT 0,
    last_love_daily BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS marriage_guild_config (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    polygamy BOOLEAN DEFAULT FALSE,
    max_spouses INT DEFAULT 1,
    announce_channel BIGINT,
    marriage_role BIGINT
);

CREATE TABLE IF NOT EXISTS marriage_gifts (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    from_id TEXT,
    to_id TEXT,
    gift_type TEXT,
    love_points INT DEFAULT 0,
    given_at BIGINT
);

-- ── Temp Channels / TempVoice ────────────────────────────
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
    control_channel_id BIGINT,
    lang TEXT DEFAULT 'mn'
);

-- Existing databases may already have guild_config without the lang column
-- (CREATE TABLE IF NOT EXISTS will not add columns). Backfill it here.
ALTER TABLE guild_config ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'mn';

-- ── Lottery ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lottery (
    id INT PRIMARY KEY,
    pool BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lottery_entries (
    user_id TEXT,
    guild_id TEXT,
    tickets INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Staff Tables ─────────────────────────────────────────
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

-- ── Giveaways ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS giveaways (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    channel_id BIGINT,
    message_id BIGINT,
    prize TEXT,
    winner_count INT DEFAULT 1,
    end_time BIGINT,
    host_id TEXT,
    required_role_id BIGINT,
    ended BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS giveaway_entries (
    giveaway_id INT,
    user_id TEXT,
    PRIMARY KEY (giveaway_id, user_id)
);

-- ── Games / Casino stats ─────────────────────────────────
CREATE TABLE IF NOT EXISTS game_stats (
    user_id TEXT,
    guild_id TEXT,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    total_won BIGINT DEFAULT 0,
    total_bet BIGINT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Role Income ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS role_income (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    amount BIGINT NOT NULL DEFAULT 1000,
    interval_seconds BIGINT NOT NULL DEFAULT 3600
);

-- ── Shop / Inventory ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS shop_stock (
    guild_id TEXT,
    item_id INT,
    current_stock INT DEFAULT 0,
    last_restock BIGINT,
    PRIMARY KEY (guild_id, item_id)
);

CREATE TABLE IF NOT EXISTS user_inventory (
    user_id TEXT,
    guild_id TEXT,
    item_id INT,
    quantity INT DEFAULT 1,
    PRIMARY KEY (user_id, guild_id, item_id)
);

CREATE TABLE IF NOT EXISTS user_drunk (
    user_id TEXT,
    guild_id TEXT,
    level INT DEFAULT 0,
    last_update BIGINT,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS user_equips (
    guild_id TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    slot     TEXT NOT NULL,      -- ring | necklace | bracelet | charm
    item_id  BIGINT NOT NULL,
    updated_at BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, slot)
);

CREATE TABLE IF NOT EXISTS marketplace_listings (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    seller_id TEXT,
    item_id INT,
    quantity INT,
    price_per_item INT,
    created_at BIGINT
);

-- ── Counting ─────────────────────────────────────────────
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

-- ── Confessions ──────────────────────────────────────────
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

-- ── Avatar log ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS avatar_log_config (
    guild_id TEXT PRIMARY KEY,
    log_channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE
);

-- ── Invite tracking ──────────────────────────────────────
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
    left_at BIGINT,
    is_fake BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS daily_stats (
    guild_id TEXT,
    date TEXT,
    joins INT DEFAULT 0,
    leaves INT DEFAULT 0,
    PRIMARY KEY (guild_id, date)
);

CREATE TABLE IF NOT EXISTS invite_labels (
    guild_id TEXT,
    invite_code TEXT,
    label TEXT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, invite_code)
);

-- ── Sticky messages ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS sticky_messages (
    guild_id TEXT,
    channel_id TEXT,
    message_id TEXT,
    content TEXT,
    updated_at BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

-- ── Temp Roles ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS temproles (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    role_id BIGINT,
    end_time BIGINT
);

CREATE TABLE IF NOT EXISTS temprole_config (
    guild_id TEXT PRIMARY KEY,
    max_duration_seconds INT DEFAULT 604800
);

-- ── PvP cooldowns ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pvp_cooldowns (
    guild_id TEXT,
    user_id TEXT,
    last_used BIGINT,
    PRIMARY KEY (guild_id, user_id)
);

-- ── Quests ───────────────────────────────────────────────
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

-- ── Greetings / Templates ────────────────────────────────
CREATE TABLE IF NOT EXISTS greeting_templates (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    creator_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

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

-- ── Economy phrase / income / config tables ──────────────
CREATE TABLE IF NOT EXISTS work_phrases (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    phrase TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_cooldowns_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    cooldown_seconds INT DEFAULT 30,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_fines_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    fine_min BIGINT DEFAULT 100,
    fine_max BIGINT DEFAULT 1000,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_payouts_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    payout_min BIGINT DEFAULT 1000,
    payout_max BIGINT DEFAULT 5000,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_fail_rates (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    fail_rate FLOAT DEFAULT 0.3,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS custom_replies (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    type TEXT DEFAULT 'success',
    text TEXT NOT NULL
);

-- ── Auto-moderation ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS automod_config (
    guild_id TEXT,
    feature TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TEXT,
    PRIMARY KEY (guild_id, feature)
);

-- ── Reaction roles ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id TEXT,
    message_id TEXT,
    emoji TEXT,
    role_id TEXT,
    created_at TEXT,
    PRIMARY KEY (guild_id, message_id, emoji)
);

-- ── Bot heartbeat (website status page) ──────────────────
-- supabase_manager.ping_bot() upserts id=1 with status/last_ping/uptime_since;
-- The bot writes this row; the FastAPI backend exposes a sanitized status.
CREATE TABLE IF NOT EXISTS bot_status (
    id INT PRIMARY KEY DEFAULT 1,
    status TEXT DEFAULT 'offline',
    last_ping TIMESTAMPTZ,
    uptime_since TIMESTAMPTZ
);
INSERT INTO bot_status (id, status) VALUES (1, 'offline')
ON CONFLICT (id) DO NOTHING;

-- ── RPC: atomic increment helper ─────────────────────────
CREATE OR REPLACE FUNCTION increment(
    table_name TEXT,
    filter_col TEXT,
    filter_val TEXT,
    col TEXT,
    delta BIGINT
) RETURNS VOID LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I SET %I = COALESCE(%I, 0) + %s WHERE %I = %L',
        table_name, col, col, delta, filter_col, filter_val
    );
END;
$$;

-- ── RPC: atomic stock consumption (negative-ыг хориглоно) ─
CREATE OR REPLACE FUNCTION consume_stock(
    g_guild_id TEXT,
    g_item_id TEXT,
    g_quantity INTEGER
) RETURNS BOOLEAN LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    updated BOOLEAN;
BEGIN
    UPDATE shop_stock
    SET current_stock = current_stock - g_quantity
    WHERE guild_id = g_guild_id
      AND item_id = g_item_id
      AND current_stock >= g_quantity
    RETURNING TRUE INTO updated;
    RETURN COALESCE(updated, FALSE);
END;
$$;

-- ── Indexes ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_economy_balance ON economy (balance);
CREATE INDEX IF NOT EXISTS idx_economy_guild ON economy (guild_id, balance);
CREATE INDEX IF NOT EXISTS idx_levels_guild ON levels (guild_id, level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_temproles_guild ON temproles (guild_id);
CREATE INDEX IF NOT EXISTS idx_temproles_end ON temproles (end_time);
CREATE INDEX IF NOT EXISTS idx_giveaways_guild ON giveaways (guild_id);
CREATE INDEX IF NOT EXISTS idx_giveaways_end ON giveaways (end_time);
CREATE INDEX IF NOT EXISTS idx_role_income_guild ON role_income (guild_id);
CREATE INDEX IF NOT EXISTS idx_game_stats_guild ON game_stats (guild_id, total_won DESC);
CREATE INDEX IF NOT EXISTS idx_shop_stock_guild ON shop_stock (guild_id);

-- ── Row-level security ─────────────────────────────────
-- Server processes use a service-role/secret key. Public roles are denied
-- by default; only the sanitized bot heartbeat is intentionally readable.
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
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'allow_all_' || t, t);
        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
    END LOOP;
END;
$$;

-- ============================================================================
-- SECTION 4: Least-privilege Data API grants
-- -----------------------------------------------------------------------------
-- New tables/functions remain private until explicitly exposed.
-- ============================================================================
GRANT SELECT ON TABLE public.bot_status TO anon;
DROP POLICY IF EXISTS anon_read_bot_status ON public.bot_status;
CREATE POLICY anon_read_bot_status ON public.bot_status
  FOR SELECT TO anon USING (id = 1);
REVOKE ALL ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
  TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE USAGE, SELECT ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- Tell PostgREST to refresh its schema cache after applying grants
NOTIFY pgrst, 'reload schema';

-- ============ END: 000_complete_schema.sql ============


-- ============ BEGIN: 20260813_runtime_missing_tables.sql ============
-- =============================================================
-- Migration: 20260813_runtime_missing_tables.sql
-- Bot: 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹
-- Purpose: Restore tables that are missing from the live Supabase
--          project so that background tasks and cogs can query
--          them without PGRST205 / HTTP 404.
--
-- This migration is NON-DESTRUCTIVE: every statement uses
--   CREATE TABLE IF NOT EXISTS,
--   CREATE INDEX IF NOT EXISTS,
--   CREATE OR REPLACE FUNCTION.
-- No DROP / TRUNCATE / DELETE is executed.
-- =============================================================

-- ── Economy ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS economy (
    user_id TEXT,
    guild_id TEXT,
    balance BIGINT DEFAULT 1000,
    bank_balance BIGINT DEFAULT 0,
    last_daily BIGINT,
    last_work BIGINT,
    bank_protect_until BIGINT DEFAULT 0,
    prison_until BIGINT DEFAULT 0,
    hunger INT DEFAULT 0,
    mood INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Levels ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS levels (
    user_id TEXT,
    guild_id TEXT,
    xp BIGINT DEFAULT 0,
    level INT DEFAULT 1,
    message_count INT DEFAULT 0,
    voice_seconds BIGINT DEFAULT 0,
    reaction_count INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS leveling_config (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    announce_channel BIGINT,
    voice_xp_enabled BOOLEAN DEFAULT TRUE,
    prog_type TEXT DEFAULT 'arithmetic',
    prog_base INT DEFAULT 100,
    prog_step FLOAT DEFAULT 150,
    xp_tiers TEXT,
    xp_media INT DEFAULT 15,
    xp_reaction INT DEFAULT 1,
    xp_voice_silent INT DEFAULT 5,
    xp_voice_talking INT DEFAULT 15,
    msg_cooldown INT DEFAULT 60,
    react_cooldown INT DEFAULT 10,
    background_url TEXT,
    font_name TEXT,
    xp_drop_enabled BOOLEAN DEFAULT FALSE,
    xp_drop_channel BIGINT,
    xp_drop_min INT DEFAULT 100,
    xp_drop_max INT DEFAULT 500,
    xp_drop_interval INT DEFAULT 3600,
    cafe_buff_enabled BOOLEAN DEFAULT TRUE,
    invite_xp INT DEFAULT 0,
    marriage_bonus FLOAT DEFAULT 0.1
);

CREATE TABLE IF NOT EXISTS level_roles (
    guild_id TEXT,
    level INT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS level_rewards (
    guild_id TEXT,
    level INT,
    money INT DEFAULT 0,
    PRIMARY KEY (guild_id, level)
);

CREATE TABLE IF NOT EXISTS leveling_exceptions (
    guild_id TEXT,
    type TEXT,
    target_id TEXT,
    PRIMARY KEY (guild_id, type, target_id)
);

-- ── Warnings ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    moderator_id TEXT,
    reason TEXT,
    timestamp BIGINT
);

-- ── Marriages ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS marriages (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    partner_id TEXT,
    guild_id TEXT,
    marriage_date TEXT,
    ring_name TEXT,
    ring_emoji TEXT,
    love_points INT DEFAULT 0,
    UNIQUE (user_id, partner_id, guild_id)
);

CREATE TABLE IF NOT EXISTS marriage_proposals (
    guild_id TEXT,
    from_id TEXT,
    to_id TEXT,
    proposal_type TEXT,
    ring_id INT DEFAULT 0,
    expires_at BIGINT,
    PRIMARY KEY (guild_id, from_id, to_id, proposal_type)
);

CREATE TABLE IF NOT EXISTS adoptions (
    guild_id TEXT,
    parent_id TEXT,
    child_id TEXT,
    type TEXT DEFAULT 'adoption',
    adopted_since BIGINT,
    PRIMARY KEY (guild_id, parent_id, child_id)
);

CREATE TABLE IF NOT EXISTS marriage_user_settings (
    guild_id TEXT,
    user_id TEXT,
    blocked BOOLEAN DEFAULT FALSE,
    auto_accept_marriage BOOLEAN DEFAULT FALSE,
    last_gift_daily BIGINT DEFAULT 0,
    last_love_daily BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS marriage_guild_config (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN DEFAULT TRUE,
    polygamy BOOLEAN DEFAULT FALSE,
    max_spouses INT DEFAULT 1,
    announce_channel BIGINT,
    marriage_role BIGINT
);

CREATE TABLE IF NOT EXISTS marriage_gifts (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    from_id TEXT,
    to_id TEXT,
    gift_type TEXT,
    love_points INT DEFAULT 0,
    given_at BIGINT
);

-- ── Temp Channels / TempVoice ────────────────────────────
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

-- ── Lottery ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lottery (
    id INT PRIMARY KEY,
    pool BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS lottery_entries (
    user_id TEXT,
    guild_id TEXT,
    tickets INT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Staff Tables ─────────────────────────────────────────
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

-- ── Giveaways ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS giveaways (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    channel_id BIGINT,
    message_id BIGINT,
    prize TEXT,
    winner_count INT DEFAULT 1,
    end_time BIGINT,
    host_id TEXT,
    required_role_id BIGINT,
    ended BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS giveaway_entries (
    giveaway_id INT,
    user_id TEXT,
    PRIMARY KEY (giveaway_id, user_id)
);

-- ── Games / Casino stats ─────────────────────────────────
CREATE TABLE IF NOT EXISTS game_stats (
    user_id TEXT,
    guild_id TEXT,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    total_won BIGINT DEFAULT 0,
    total_bet BIGINT DEFAULT 0,
    PRIMARY KEY (user_id, guild_id)
);

-- ── Role Income ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS role_income (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    role_id BIGINT NOT NULL,
    amount BIGINT NOT NULL DEFAULT 1000,
    interval_seconds BIGINT NOT NULL DEFAULT 3600
);

-- ── Shop / Inventory ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS shop_stock (
    guild_id TEXT,
    item_id INT,
    current_stock INT DEFAULT 0,
    last_restock BIGINT,
    PRIMARY KEY (guild_id, item_id)
);

CREATE TABLE IF NOT EXISTS user_inventory (
    user_id TEXT,
    guild_id TEXT,
    item_id INT,
    quantity INT DEFAULT 1,
    PRIMARY KEY (user_id, guild_id, item_id)
);

CREATE TABLE IF NOT EXISTS user_drunk (
    user_id TEXT,
    guild_id TEXT,
    level INT DEFAULT 0,
    last_update BIGINT,
    PRIMARY KEY (user_id, guild_id)
);

CREATE TABLE IF NOT EXISTS marketplace_listings (
    id SERIAL PRIMARY KEY,
    guild_id TEXT,
    seller_id TEXT,
    item_id INT,
    quantity INT,
    price_per_item INT,
    created_at BIGINT
);

-- ── Counting ─────────────────────────────────────────────
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

-- ── Confessions ──────────────────────────────────────────
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

-- ── Avatar log ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS avatar_log_config (
    guild_id TEXT PRIMARY KEY,
    log_channel_id BIGINT,
    enabled BOOLEAN DEFAULT TRUE
);

-- ── Invite tracking ──────────────────────────────────────
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
    left_at BIGINT,
    is_fake BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS daily_stats (
    guild_id TEXT,
    date TEXT,
    joins INT DEFAULT 0,
    leaves INT DEFAULT 0,
    PRIMARY KEY (guild_id, date)
);

CREATE TABLE IF NOT EXISTS invite_labels (
    guild_id TEXT,
    invite_code TEXT,
    label TEXT,
    role_id BIGINT,
    PRIMARY KEY (guild_id, invite_code)
);

-- ── Sticky messages ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS sticky_messages (
    guild_id TEXT,
    channel_id TEXT,
    message_id TEXT,
    content TEXT,
    updated_at BIGINT,
    PRIMARY KEY (guild_id, channel_id)
);

-- ── Temp Roles ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS temproles (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    role_id BIGINT,
    end_time BIGINT
);

CREATE TABLE IF NOT EXISTS temprole_config (
    guild_id TEXT PRIMARY KEY,
    max_duration_seconds INT DEFAULT 604800
);

-- ── PvP cooldowns ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pvp_cooldowns (
    guild_id TEXT,
    user_id TEXT,
    last_used BIGINT,
    PRIMARY KEY (guild_id, user_id)
);

-- ── Quests ───────────────────────────────────────────────
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

-- ── Greetings / Templates ────────────────────────────────
CREATE TABLE IF NOT EXISTS greeting_templates (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    creator_id TEXT NOT NULL,
    name TEXT NOT NULL,
    data TEXT NOT NULL,
    created_at BIGINT DEFAULT (EXTRACT(EPOCH FROM NOW()))
);

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

-- ── Economy phrase / income / config tables ──────────────
CREATE TABLE IF NOT EXISTS work_phrases (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    phrase TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS economy_cooldowns_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    cooldown_seconds INT DEFAULT 30,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_fines_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    fine_min BIGINT DEFAULT 100,
    fine_max BIGINT DEFAULT 1000,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_payouts_config (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    payout_min BIGINT DEFAULT 1000,
    payout_max BIGINT DEFAULT 5000,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS economy_fail_rates (
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    fail_rate FLOAT DEFAULT 0.3,
    PRIMARY KEY (guild_id, command)
);

CREATE TABLE IF NOT EXISTS custom_replies (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    command TEXT NOT NULL,
    type TEXT DEFAULT 'success',
    text TEXT NOT NULL
);

-- ── Auto-moderation ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS automod_config (
    guild_id TEXT,
    feature TEXT,
    enabled BOOLEAN DEFAULT true,
    created_at TEXT,
    PRIMARY KEY (guild_id, feature)
);

-- ── Reaction roles ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id TEXT,
    message_id TEXT,
    emoji TEXT,
    role_id TEXT,
    created_at TEXT,
    PRIMARY KEY (guild_id, message_id, emoji)
);

-- ── RPC: atomic increment helper ─────────────────────────
CREATE OR REPLACE FUNCTION increment(
    table_name TEXT,
    filter_col TEXT,
    filter_val TEXT,
    col TEXT,
    delta BIGINT
) RETURNS VOID LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I SET %I = COALESCE(%I, 0) + %s WHERE %I = %L',
        table_name, col, col, delta, filter_col, filter_val
    );
END;
$$;

-- ── RPC: atomic stock consumption (negative-ыг хориглоно) ─
CREATE OR REPLACE FUNCTION consume_stock(
    g_guild_id TEXT,
    g_item_id TEXT,
    g_quantity INTEGER
) RETURNS BOOLEAN LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    updated BOOLEAN;
BEGIN
    UPDATE shop_stock
    SET current_stock = current_stock - g_quantity
    WHERE guild_id = g_guild_id
      AND item_id = g_item_id
      AND current_stock >= g_quantity
    RETURNING TRUE INTO updated;
    RETURN COALESCE(updated, FALSE);
END;
$$;

-- ── Indexes ──────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_economy_balance ON economy (balance);
CREATE INDEX IF NOT EXISTS idx_economy_guild ON economy (guild_id, balance);
CREATE INDEX IF NOT EXISTS idx_levels_guild ON levels (guild_id, level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_temproles_guild ON temproles (guild_id);
CREATE INDEX IF NOT EXISTS idx_temproles_end ON temproles (end_time);
CREATE INDEX IF NOT EXISTS idx_giveaways_guild ON giveaways (guild_id);
CREATE INDEX IF NOT EXISTS idx_giveaways_end ON giveaways (end_time);
CREATE INDEX IF NOT EXISTS idx_role_income_guild ON role_income (guild_id);
CREATE INDEX IF NOT EXISTS idx_game_stats_guild ON game_stats (guild_id, total_won DESC);
CREATE INDEX IF NOT EXISTS idx_shop_stock_guild ON shop_stock (guild_id);

-- ── Row-level security ─────────────────────────────────
-- The bot and the static status page operate with the anon (public)
-- key, so every public table enables RLS with an explicit "allow all"
-- policy (USING(true) / WITH CHECK(true)). This resolves the
-- database-linter findings (0013_rls_disabled_in_public,
-- 0007_policy_exists_rls_disabled). This fragment is idempotent.
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
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'allow_all_' || t, t);
        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
    END LOOP;
END;
$$;

-- ── Grants for anon/authenticated (required for anon key access) ──
GRANT SELECT ON TABLE public.bot_status TO anon;
DROP POLICY IF EXISTS anon_read_bot_status ON public.bot_status;
CREATE POLICY anon_read_bot_status ON public.bot_status
  FOR SELECT TO anon USING (id = 1);
REVOKE ALL ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
  TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE USAGE, SELECT ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- Tell PostgREST to refresh its schema cache after applying grants
NOTIFY pgrst, 'reload schema';

-- ============ END: 20260813_runtime_missing_tables.sql ============


-- ============ BEGIN: 20260818_lang_column.sql ============
-- AETHER i18n: серверийн хэлний тохиргоо (MN/EN)
-- ЭНЭ ФАЙЛЫГ Supabase SQL Editor дотор хуулж ажиллуул:
--   https://supabase.com/dashboard/project/zwpgweaikpjkftkzmlak/sql
-- RLS-ийн бодлоготой нийцэж байгаа тул анон (бот) key-ээр ч бичиж уншина.

-- 1. guild_config хүснэгтэд lang багана нэмэх (байхгүй бол)
ALTER TABLE IF EXISTS guild_config
ADD COLUMN IF NOT EXISTS lang TEXT DEFAULT 'mn';

-- 2. Анхны утга: хуучин серверүүд Монголоор эхлэнэ
UPDATE guild_config SET lang = 'mn' WHERE lang IS NULL;

-- 3. Багана байхгүй хүснэгтийн хувьд (first-time setup)
-- guild_config үгүй бол хүснэгтийг үүсгэнэ
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id TEXT PRIMARY KEY,
    create_channel_id BIGINT,
    max_channels_per_user INT DEFAULT 3,
    category_id BIGINT,
    control_channel_id BIGINT,
    lang TEXT DEFAULT 'mn'
);

-- ============ END: 20260818_lang_column.sql ============


-- ============ BEGIN: 20260824_equip_system.sql ============
-- AETHER: Зүүлт/гоёлын хэрэгсэл (equip) систем
-- ЭНЭ ФАЙЛЫГ Supabase SQL Editor дотор хуулж ажиллуулна уу.
--   https://supabase.com/dashboard/project/<project>/sql

-- Хэрэглэгчийн зүүсэн бараа (слот тутамд 1 бараа)
CREATE TABLE IF NOT EXISTS user_equips (
    guild_id TEXT NOT NULL,
    user_id  TEXT NOT NULL,
    slot     TEXT NOT NULL,      -- ring | necklace | bracelet | charm
    item_id  BIGINT NOT NULL,
    updated_at BIGINT DEFAULT 0,
    PRIMARY KEY (guild_id, user_id, slot)
);

-- Ботын service key RLS-ийг тойрч гарна; нийтээр унших/бичих бодлого
ALTER TABLE user_equips ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "bot full access user_equips" ON user_equips;
CREATE POLICY "bot full access user_equips"
    ON user_equips
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- ============ END: 20260824_equip_system.sql ============


-- ============ BEGIN: 20260903_enable_rls.sql ============
-- ============================================================================
-- 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 - Enable RLS on all public tables + fix increment() search_path
-- Date: 2026-09-03
--
-- Resolves the Supabase database-linter findings:
--   0007_policy_exists_rls_disabled  - bot_status has policies but RLS off
--   0013_rls_disabled_in_public      - public tables with RLS disabled
--   0011_function_search_path_mutable - increment() has a mutable search_path
--
-- Security model:
--   * Discord bot and backend use SUPABASE_SERVICE_ROLE_KEY server-side.
--   * Browser clients never receive a Supabase key.
--   * anon may only SELECT the public bot_status heartbeat (legacy clients).
--   * authenticated has no direct access until a row-scoped policy exists.
--
-- The ENABLE + policy creation is wrapped in a DO block so it is idempotent
-- and named policies are (re)created unconditionally.
-- ============================================================================

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
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'allow_all_' || t, t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'anon_read_' || t, t);
        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
    END LOOP;
END;
$$;

GRANT SELECT ON TABLE public.bot_status TO anon;
CREATE POLICY anon_read_bot_status
    ON public.bot_status FOR SELECT TO anon USING (id = 1);

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- Fix increment(): pin an immutable, safe search_path so the function cannot
-- be hijacked by a malicious schema earlier in the caller's search_path.
-- ============================================================================
ALTER FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    SET search_path = pg_catalog, public;
REVOKE ALL ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    TO service_role;

-- Tell PostgREST to refresh its schema cache
NOTIFY pgrst, 'reload schema';

-- ============ END: 20260903_enable_rls.sql ============


-- ============ BEGIN: 20260913_restore_runtime_service_role_grants.sql ============
-- Restore the server-only bot role after public access hardening.
-- This intentionally grants only tables confirmed by production runtime logs.
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.economy,
  public.levels,
  public.giveaways,
  public.temproles,
  public.role_income,
  public.tempvoice_setup_msg,
  public.user_inventory,
  public.automod_config,
  public.reaction_roles,
  public.shop_stock,
  public.leveling_config,
  public.leveling_exceptions,
  public.staff_config,
  public.marriages,
  public.adoptions
TO service_role;

NOTIFY pgrst, 'reload schema';

-- ============ END: 20260913_restore_runtime_service_role_grants.sql ============


-- ============ BEGIN: 20260914_repair_runtime_schema.sql ============
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

-- ============ BEGIN: 20260920_ticket_foundation.sql ============
CREATE TABLE IF NOT EXISTS ticket_config (
    guild_id TEXT PRIMARY KEY, category_id BIGINT, staff_role_id BIGINT,
    log_channel_id BIGINT, panel_channel_id BIGINT, panel_message_id BIGINT,
    updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY, guild_id TEXT NOT NULL, channel_id BIGINT NOT NULL UNIQUE,
    opener_id TEXT NOT NULL, subject TEXT, status TEXT NOT NULL DEFAULT 'open'
    CHECK (status IN ('open', 'closed')), claimed_by TEXT,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()), closed_at BIGINT, closed_by TEXT
);
CREATE INDEX IF NOT EXISTS ix_tickets_guild_status ON tickets (guild_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tickets_opener_status ON tickets (guild_id, opener_id, status);
ALTER TABLE ticket_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ticket_config, tickets FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON ticket_config, tickets TO service_role;
GRANT USAGE, SELECT ON SEQUENCE tickets_id_seq TO service_role;

-- ============ BEGIN: 20260920_webhook_automation.sql ============
CREATE TABLE IF NOT EXISTS automation_rules (
    id BIGSERIAL PRIMARY KEY, guild_id TEXT NOT NULL,
    event_name TEXT NOT NULL CHECK (event_name IN ('member_join', 'member_leave')),
    channel_id BIGINT NOT NULL, log_channel_id BIGINT, message_template TEXT NOT NULL,
    embed_title TEXT, embed_color BIGINT, enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT NOT NULL, created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()), UNIQUE (guild_id, event_name)
);
CREATE TABLE IF NOT EXISTS automation_runs (
    id BIGSERIAL PRIMARY KEY, rule_id BIGINT NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    guild_id TEXT NOT NULL, event_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('sent', 'skipped', 'failed')), detail TEXT,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);
CREATE INDEX IF NOT EXISTS idx_automation_rules_guild ON automation_rules(guild_id);
CREATE INDEX IF NOT EXISTS idx_automation_runs_rule_created ON automation_runs(rule_id, created_at DESC);
ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON automation_rules, automation_runs FROM anon, authenticated;
GRANT ALL ON automation_rules, automation_runs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE automation_rules_id_seq, automation_runs_id_seq TO service_role;

-- I18N is retired; fresh schema must not retain the obsolete preference.
ALTER TABLE IF EXISTS public.guild_config DROP COLUMN IF EXISTS lang;
NOTIFY pgrst, 'reload schema';

-- ============ END: 20260914_repair_runtime_schema.sql ============


-- ============ BEGIN: 20260917_government_economy.sql ============
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

-- ============ END: 20260917_government_economy.sql ============


-- ============ BEGIN: 20260917_fix_user_equips_rls.sql ============
-- ============================================================================
-- AETHER: tighten user_equips RLS (linter finding rls_policy_always_true)
-- Date: 2026-09-17
--
-- The equip system (cogs/shop.py) runs server-side with
-- SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS. No anonymous / authenticated
-- client path reads or writes user_equips, so the blanket
-- FOR ALL USING (true) WITH CHECK (true) policy only broadened access.
--
-- Remediation: drop the permissive policy, keep RLS enabled with no policies,
-- and grant service_role explicitly (it bypasses RLS regardless). The linter
-- explicitly allows SELECT USING (true) for public reads, but none is needed
-- here because the bot is the only caller.
-- ============================================================================

DROP POLICY IF EXISTS "bot full access user_equips" ON public.user_equips;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_equips TO service_role;

ALTER TABLE public.user_equips ENABLE ROW LEVEL SECURITY;

NOTIFY pgrst, 'reload schema';

-- ============ END: 20260917_fix_user_equips_rls.sql ============


-- ============ BEGIN: Anime Clash profiles ============
CREATE TABLE IF NOT EXISTS anime_clash_profiles (
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    xp INTEGER NOT NULL DEFAULT 0 CHECK (xp >= 0),
    level INTEGER NOT NULL DEFAULT 1 CHECK (level >= 1),
    wins INTEGER NOT NULL DEFAULT 0 CHECK (wins >= 0),
    losses INTEGER NOT NULL DEFAULT 0 CHECK (losses >= 0),
    best_combo INTEGER NOT NULL DEFAULT 0 CHECK (best_combo >= 0),
    total_reward BIGINT NOT NULL DEFAULT 0 CHECK (total_reward >= 0),
    favorite_hero TEXT NOT NULL DEFAULT 'samurai',
    last_daily_date DATE,
    PRIMARY KEY (user_id, guild_id)
);

CREATE INDEX IF NOT EXISTS idx_anime_clash_profiles_guild
    ON anime_clash_profiles (guild_id, level DESC, xp DESC);

ALTER TABLE anime_clash_profiles ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE anime_clash_profiles TO service_role;
NOTIFY pgrst, 'reload schema';
-- ============ END: Anime Clash profiles ============


-- ============ BEGIN: Durable Texas Poker payouts ============
CREATE TABLE IF NOT EXISTS poker_pending_payouts (
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    intent TEXT NOT NULL DEFAULT 'settlement' CHECK (intent IN ('refund', 'settlement')),
    amount BIGINT NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMPTZ,
    PRIMARY KEY (channel_id, user_id)
);

ALTER TABLE poker_pending_payouts
    ADD COLUMN IF NOT EXISTS intent TEXT NOT NULL DEFAULT 'settlement';
ALTER TABLE poker_pending_payouts
    ADD COLUMN IF NOT EXISTS settled_at TIMESTAMPTZ;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'poker_pending_payouts_intent_check'
          AND conrelid = 'poker_pending_payouts'::regclass
    ) THEN
        ALTER TABLE poker_pending_payouts
            ADD CONSTRAINT poker_pending_payouts_intent_check
            CHECK (intent IN ('refund', 'settlement'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_poker_pending_payouts_channel_guild
    ON poker_pending_payouts (channel_id, guild_id);
CREATE INDEX IF NOT EXISTS idx_poker_pending_payouts_unsettled
    ON poker_pending_payouts (channel_id, guild_id)
    WHERE settled_at IS NULL;

ALTER TABLE poker_pending_payouts ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE poker_pending_payouts TO service_role;

CREATE OR REPLACE FUNCTION begin_poker_table(p_channel_id TEXT, p_guild_id TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND settled_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Unsettled poker obligation exists';
    END IF;
    DELETE FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id;
    RETURN TRUE;
END;
$$;
COMMENT ON FUNCTION begin_poker_table(TEXT, TEXT) IS
    'Fails if unsettled obligations exist; otherwise removes settled history. It creates no persistent lock row.';

CREATE OR REPLACE FUNCTION charge_poker_buyin(
    p_channel_id TEXT, p_guild_id TEXT, p_user_id TEXT,
    p_host_id TEXT, p_amount BIGINT
) RETURNS BIGINT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_marker BIGINT;
BEGIN
    IF p_amount <= 0 THEN RAISE EXCEPTION 'Invalid poker buy-in'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND intent = 'settlement'
    ) THEN
        RAISE EXCEPTION 'Poker settlement already prepared';
    END IF;
    INSERT INTO poker_pending_payouts(channel_id, guild_id, user_id, host_id, amount, intent)
    VALUES (p_channel_id, p_guild_id, p_user_id, p_host_id, p_amount, 'refund')
    ON CONFLICT (channel_id, user_id) DO NOTHING
    RETURNING amount INTO v_marker;
    IF v_marker IS NULL THEN RAISE EXCEPTION 'Poker buy-in already charged'; END IF;
    UPDATE economy SET balance = balance - p_amount
    WHERE user_id = p_user_id AND guild_id = p_guild_id AND balance >= p_amount;
    IF NOT FOUND THEN RAISE EXCEPTION 'Insufficient poker balance'; END IF;
    RETURN p_amount;
END;
$$;

DROP FUNCTION IF EXISTS prepare_poker_settlement(TEXT, TEXT, TEXT, JSONB);
CREATE OR REPLACE FUNCTION prepare_poker_settlement(
    p_channel_id TEXT, p_guild_id TEXT, p_host_id TEXT,
    p_expected_total BIGINT, p_payouts JSONB
) RETURNS INTEGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_count INTEGER; v_plan_total BIGINT; v_refund_total BIGINT;
BEGIN
    IF p_expected_total <= 0 THEN
        RAISE EXCEPTION 'Poker expected total must be positive';
    END IF;
    IF jsonb_typeof(p_payouts) <> 'array' OR jsonb_array_length(p_payouts) = 0 THEN
        RAISE EXCEPTION 'Poker settlement plan is empty';
    END IF;
    IF EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_payouts) AS item
        WHERE jsonb_typeof(item) <> 'object'
           OR NULLIF(BTRIM(item->>'user_id'), '') IS NULL
           OR COALESCE(item->>'amount', '') !~ '^[0-9]+$'
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains an invalid payout';
    END IF;
    IF EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_payouts) AS item
        WHERE (item->>'amount')::BIGINT <= 0
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains an invalid payout';
    END IF;
    IF (
        SELECT COUNT(*) FROM jsonb_array_elements(p_payouts)
    ) <> (
        SELECT COUNT(DISTINCT item->>'user_id') FROM jsonb_array_elements(p_payouts) AS item
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains duplicate users';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND settled_at IS NULL AND host_id <> p_host_id
    ) THEN
        RAISE EXCEPTION 'Poker settlement contains another host';
    END IF;
    SELECT COALESCE(SUM((item->>'amount')::BIGINT), 0) INTO v_plan_total
    FROM jsonb_array_elements(p_payouts) AS item;
    SELECT COALESCE(SUM(amount), 0) INTO v_refund_total
    FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id
      AND host_id = p_host_id AND intent = 'refund' AND settled_at IS NULL;
    IF v_plan_total <> p_expected_total OR v_refund_total <> p_expected_total THEN
        RAISE EXCEPTION 'Poker settlement total mismatch: plan %, committed %, expected %',
            v_plan_total, v_refund_total, p_expected_total;
    END IF;
    DELETE FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id
      AND settled_at IS NULL;
    INSERT INTO poker_pending_payouts(channel_id, guild_id, user_id, host_id, amount, intent)
    SELECT p_channel_id, p_guild_id, item->>'user_id', p_host_id,
           (item->>'amount')::BIGINT, 'settlement'
    FROM jsonb_array_elements(p_payouts) AS item
    WHERE (item->>'amount')::BIGINT > 0;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count = 0 THEN RAISE EXCEPTION 'Poker settlement plan has no payouts'; END IF;
    RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION charge_poker_buyin(TEXT, TEXT, TEXT, TEXT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION charge_poker_buyin(TEXT, TEXT, TEXT, TEXT, BIGINT) TO service_role;
REVOKE ALL ON FUNCTION begin_poker_table(TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION begin_poker_table(TEXT, TEXT) TO service_role;
REVOKE ALL ON FUNCTION prepare_poker_settlement(TEXT, TEXT, TEXT, BIGINT, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION prepare_poker_settlement(TEXT, TEXT, TEXT, BIGINT, JSONB) TO service_role;

CREATE OR REPLACE FUNCTION settle_poker_payout(
    p_channel_id TEXT,
    p_guild_id TEXT,
    p_user_id TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_amount BIGINT;
    v_row_guild_id TEXT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    UPDATE poker_pending_payouts
    SET settled_at = NOW()
    WHERE channel_id = p_channel_id
      AND guild_id = p_guild_id
      AND user_id = p_user_id
      AND settled_at IS NULL
    RETURNING amount, guild_id INTO v_amount, v_row_guild_id;
    IF v_amount IS NULL THEN RETURN 0; END IF;
    UPDATE economy SET balance = COALESCE(balance, 0) + v_amount
    WHERE user_id = p_user_id AND guild_id = v_row_guild_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Economy account not found for user % guild %', p_user_id, p_guild_id;
    END IF;
    RETURN v_amount;
END;
$$;

REVOKE ALL ON FUNCTION settle_poker_payout(TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION settle_poker_payout(TEXT, TEXT, TEXT) TO service_role;
NOTIFY pgrst, 'reload schema';
-- ============ END: Durable Texas Poker payouts ============


-- ============ BEGIN: Idempotent Economy balance updates ============
CREATE TABLE IF NOT EXISTS economy_balance_references (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    delta BIGINT NOT NULL,
    tax BIGINT NOT NULL DEFAULT 0,
    balance_after BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Also upgrade databases that previously applied migration 003.
ALTER TABLE economy_balance_references
    ADD COLUMN IF NOT EXISTS tax BIGINT NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS ix_economy_balance_references_created_at
    ON economy_balance_references (created_at);

ALTER TABLE economy_balance_references ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE economy_balance_references TO service_role;

CREATE OR REPLACE FUNCTION apply_economy_balance_once(
    p_reference TEXT,
    p_user_id TEXT,
    p_guild_id TEXT,
    p_delta BIGINT,
    p_max_balance BIGINT
) RETURNS TABLE(applied BOOLEAN, balance BIGINT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing economy_balance_references%ROWTYPE;
    v_balance BIGINT;
BEGIN
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_max_balance < 0 THEN
        RAISE EXCEPTION 'max balance must be non-negative';
    END IF;

    INSERT INTO economy_balance_references (reference, user_id, guild_id, delta, tax)
    VALUES (p_reference, p_user_id, p_guild_id, p_delta, 0)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        SELECT * INTO v_existing
        FROM economy_balance_references
        WHERE reference = p_reference;

        IF v_existing.user_id IS DISTINCT FROM p_user_id
           OR v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.delta IS DISTINCT FROM p_delta
           OR v_existing.tax IS DISTINCT FROM 0 THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.balance_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed balance result', p_reference;
        END IF;

        RETURN QUERY SELECT FALSE, v_existing.balance_after;
        RETURN;
    END IF;

    UPDATE economy
    SET balance = LEAST(p_max_balance, COALESCE(economy.balance, 0) + p_delta)
    WHERE user_id = p_user_id
      AND guild_id = p_guild_id
      AND COALESCE(economy.balance, 0) + p_delta >= 0
    RETURNING economy.balance INTO v_balance;

    IF v_balance IS NULL THEN
        IF EXISTS (
            SELECT 1 FROM economy
            WHERE user_id = p_user_id AND guild_id = p_guild_id
        ) THEN
            RAISE EXCEPTION 'insufficient balance for user % in guild %', p_user_id, p_guild_id;
        END IF;
        RAISE EXCEPTION 'economy account not found for user % in guild %', p_user_id, p_guild_id;
    END IF;

    UPDATE economy_balance_references
    SET balance_after = v_balance
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_balance;
END;
$$;

REVOKE ALL ON FUNCTION apply_economy_balance_once(TEXT, TEXT, TEXT, BIGINT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION apply_economy_balance_once(TEXT, TEXT, TEXT, BIGINT, BIGINT) TO service_role;

NOTIFY pgrst, 'reload schema';
-- ============ END: Idempotent Economy balance updates ============

-- ============ BEGIN: Atomic confession ID allocation ============
CREATE OR REPLACE FUNCTION allocate_confession_id(p_guild_id TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_allocated BIGINT;
BEGIN
    UPDATE confession_config
    SET next_id = next_id + 1
    WHERE guild_id = p_guild_id
    RETURNING next_id - 1 INTO v_allocated;

    IF v_allocated IS NULL THEN
        RAISE EXCEPTION 'confession config not found for guild %', p_guild_id;
    END IF;

    RETURN v_allocated;
END;
$$;

REVOKE ALL ON FUNCTION allocate_confession_id(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION allocate_confession_id(TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
-- ============ END: Atomic confession ID allocation ============

-- ============ BEGIN: Atomic reward + tax distribution (2026-10-02) ============
-- apply_economy_balance_with_tax_once: atomically claims a reference, updates
-- recipient balance, credits tax recipients, increments treasury, and writes
-- ledger entries in a single transaction. Idempotent via reference key.
CREATE OR REPLACE FUNCTION apply_economy_balance_with_tax_once(
    p_reference TEXT,
    p_user_id TEXT,
    p_guild_id TEXT,
    p_delta BIGINT,
    p_max_balance BIGINT,
    p_tax BIGINT,
    p_credits JSONB,
    p_treasury BIGINT,
    p_discarded BIGINT
) RETURNS TABLE(
    applied BOOLEAN,
    balance BIGINT,
    tax_shipped BIGINT,
    treasury BIGINT,
    discarded BIGINT
) LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing economy_balance_references%ROWTYPE;
    v_balance BIGINT;
    v_credit_record RECORD;
    v_tax_shipped BIGINT := 0;
BEGIN
    -- Validate inputs
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_max_balance < 0 THEN
        RAISE EXCEPTION 'max balance must be non-negative';
    END IF;
    IF p_tax < 0 THEN
        RAISE EXCEPTION 'tax must be non-negative';
    END IF;
    IF p_treasury < 0 THEN
        RAISE EXCEPTION 'treasury must be non-negative';
    END IF;
    IF p_discarded < 0 THEN
        RAISE EXCEPTION 'discarded must be non-negative';
    END IF;

    -- Verify credits JSONB is an array of objects with user_id, amount
    IF p_credits IS NOT NULL AND jsonb_typeof(p_credits) <> 'array' THEN
        RAISE EXCEPTION 'credits must be a JSON array';
    END IF;
    IF p_credits IS NOT NULL AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_credits) AS elem
        WHERE jsonb_typeof(elem) <> 'object'
           OR COALESCE(elem->>'user_id', '') !~ '^[0-9]+$'
           OR COALESCE(elem->>'amount', '') !~ '^[0-9]+$'
    ) THEN
        RAISE EXCEPTION 'credits entries must contain numeric user_id and amount';
    END IF;
    IF p_credits IS NOT NULL AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_credits) AS elem
        GROUP BY elem->>'user_id'
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'credits user_id values must be unique';
    END IF;
    IF COALESCE((
        SELECT SUM((elem->>'amount')::BIGINT)
        FROM jsonb_array_elements(COALESCE(p_credits, '[]'::JSONB)) AS elem
    ), 0) + p_treasury + p_discarded <> p_tax THEN
        RAISE EXCEPTION 'tax distribution must equal tax amount';
    END IF;

    -- Claim the reference (idempotency key)
    INSERT INTO economy_balance_references (reference, user_id, guild_id, delta, tax)
    VALUES (p_reference, p_user_id, p_guild_id, p_delta, p_tax)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        -- Reference already exists: verify payload matches, return committed result
        SELECT * INTO v_existing
        FROM economy_balance_references
        WHERE reference = p_reference;

        IF v_existing.user_id IS DISTINCT FROM p_user_id
           OR v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.delta IS DISTINCT FROM p_delta
           OR v_existing.tax IS DISTINCT FROM p_tax THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.balance_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed balance result', p_reference;
        END IF;

        -- Return the originally committed result (no re-distribution)
        RETURN QUERY SELECT FALSE, v_existing.balance_after, 0::BIGINT, 0::BIGINT, 0::BIGINT;
        RETURN;
    END IF;

    -- Initialize without crediting, then lock/update the account atomically.
    INSERT INTO economy (user_id, guild_id, balance)
    VALUES (p_user_id, p_guild_id, 0)
    ON CONFLICT (user_id, guild_id) DO NOTHING;
    UPDATE economy
    SET balance = LEAST(p_max_balance, COALESCE(economy.balance, 0) + p_delta)
    WHERE user_id = p_user_id
      AND guild_id = p_guild_id
      AND COALESCE(economy.balance, 0) + p_delta >= 0
    RETURNING economy.balance INTO v_balance;

    IF v_balance IS NULL THEN
        RAISE EXCEPTION 'insufficient balance for user % in guild %', p_user_id, p_guild_id;
    END IF;

    -- 2. Credit tax recipients (ON CONFLICT DO NOTHING for account init, then add amount)
    IF p_credits IS NOT NULL AND jsonb_array_length(p_credits) > 0 THEN
        FOR v_credit_record IN
            SELECT (elem->>'user_id')::TEXT AS uid, (elem->>'amount')::BIGINT AS amt
            FROM jsonb_array_elements(p_credits) AS elem
        LOOP
            IF v_credit_record.amt > 0 THEN
                INSERT INTO economy (user_id, guild_id, balance)
                VALUES (v_credit_record.uid, p_guild_id, v_credit_record.amt)
                ON CONFLICT (user_id, guild_id) DO UPDATE
                    SET balance = LEAST(p_max_balance, economy.balance + v_credit_record.amt);
                v_tax_shipped := v_tax_shipped + v_credit_record.amt;
            END IF;
        END LOOP;
    END IF;

    -- 3. Increment treasury
    IF p_treasury > 0 THEN
        UPDATE economy_guild_settings
        SET treasury_balance = treasury_balance + p_treasury,
            updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
        WHERE guild_id = p_guild_id;
    END IF;

    -- 4. Write ledger entries (best-effort within transaction)
    -- Main balance change
    INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, balance_before, balance_after, reason, created_at)
    VALUES (p_guild_id, p_user_id, p_user_id, 'work', p_delta, v_balance - p_delta, v_balance, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);

    -- Tax collected
    IF p_tax > 0 THEN
        INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, metadata, created_at)
        VALUES (p_guild_id, p_user_id, p_user_id, 'tax_collected', p_tax, 'tax_atomic_reward', jsonb_build_object('shipped', v_tax_shipped, 'treasury', p_treasury, 'discarded', p_discarded), EXTRACT(EPOCH FROM NOW())::BIGINT);
    END IF;

    -- Individual tax credits
    IF p_credits IS NOT NULL AND jsonb_array_length(p_credits) > 0 THEN
        FOR v_credit_record IN
            SELECT (elem->>'user_id')::TEXT AS uid, (elem->>'amount')::BIGINT AS amt
            FROM jsonb_array_elements(p_credits) AS elem
        LOOP
            IF v_credit_record.amt > 0 THEN
                INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
                VALUES (p_guild_id, v_credit_record.uid, p_user_id, 'tax_distributed', v_credit_record.amt, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);
            END IF;
        END LOOP;
    END IF;

    -- Treasury share
    IF p_treasury > 0 THEN
        INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
        VALUES (p_guild_id, NULL, p_user_id, 'treasury_deposit', p_treasury, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);
    END IF;

    -- 5. Record the completed balance in the reference table
    UPDATE economy_balance_references
    SET balance_after = v_balance
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_balance, v_tax_shipped, p_treasury, p_discarded;
END;
$$;

REVOKE ALL ON FUNCTION apply_economy_balance_with_tax_once(TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION apply_economy_balance_with_tax_once(TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) TO service_role;

NOTIFY pgrst, 'reload schema';
-- ============ END: Atomic reward + tax distribution ============

-- ============ BEGIN: Atomic treasury payments (2026-10-02) ============
-- treasury_payments table for idempotency
CREATE TABLE IF NOT EXISTS treasury_payments (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    guild_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    amount BIGINT NOT NULL,
    recipient_ids BIGINT[] NOT NULL,
    reason TEXT,
    treasury_after BIGINT,
    credits JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_treasury_payments_created_at
    ON treasury_payments (created_at);

ALTER TABLE treasury_payments ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE treasury_payments TO service_role;

-- treasury_pay_once RPC
CREATE OR REPLACE FUNCTION treasury_pay_once(
    p_reference TEXT,
    p_guild_id TEXT,
    p_actor_id TEXT,
    p_amount BIGINT,
    p_recipient_ids BIGINT[],
    p_reason TEXT
) RETURNS TABLE(
    applied BOOLEAN,
    treasury_after BIGINT,
    credits JSONB
) LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing treasury_payments%ROWTYPE;
    v_treasury_before BIGINT;
    v_treasury_after BIGINT;
    v_recipient_count INT;
    v_share BIGINT;
    v_remainder BIGINT;
    v_credit_json JSONB := '[]'::JSONB;
    v_uid BIGINT;
    v_amt BIGINT;
    v_idx INT := 0;
BEGIN
    -- Validate inputs
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'amount must be positive';
    END IF;
    IF p_recipient_ids IS NULL OR array_length(p_recipient_ids, 1) IS NULL THEN
        RAISE EXCEPTION 'recipient_ids must be a non-empty array';
    END IF;
    v_recipient_count := array_length(p_recipient_ids, 1);
    IF v_recipient_count > 50 THEN
        RAISE EXCEPTION 'maximum 50 recipients per payment';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM unnest(p_recipient_ids) AS recipient_id
        GROUP BY recipient_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'recipient_ids must be unique';
    END IF;
    IF p_amount > 100000000000 THEN
        RAISE EXCEPTION 'amount exceeds maximum (100B)';
    END IF;
    IF char_length(COALESCE(p_reason, '')) > 200 THEN
        RAISE EXCEPTION 'reason exceeds maximum length (200)';
    END IF;

    -- Claim the reference (idempotency key)
    INSERT INTO treasury_payments (reference, guild_id, actor_id, amount, recipient_ids, reason)
    VALUES (p_reference, p_guild_id, p_actor_id, p_amount, p_recipient_ids, p_reason)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        -- Reference already exists: verify payload matches, return committed result
        SELECT * INTO v_existing
        FROM treasury_payments
        WHERE reference = p_reference;

        IF v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.actor_id IS DISTINCT FROM p_actor_id
           OR v_existing.amount IS DISTINCT FROM p_amount
           OR v_existing.recipient_ids IS DISTINCT FROM p_recipient_ids
           OR v_existing.reason IS DISTINCT FROM p_reason THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.treasury_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed treasury result', p_reference;
        END IF;

        -- Return the originally committed result (no re-credit)
        RETURN QUERY SELECT FALSE, v_existing.treasury_after, v_existing.credits;
        RETURN;
    END IF;

    -- Check treasury balance and debit atomically
    UPDATE economy_guild_settings
    SET treasury_balance = treasury_balance - p_amount,
        updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
    WHERE guild_id = p_guild_id
      AND treasury_balance >= p_amount
    RETURNING treasury_balance INTO v_treasury_after;

    IF v_treasury_after IS NULL THEN
        RAISE EXCEPTION 'insufficient treasury balance for guild %', p_guild_id;
    END IF;

    -- Credit recipients (equal split, remainder to first)
    v_share := p_amount / v_recipient_count;
    v_remainder := p_amount % v_recipient_count;

    FOR v_idx IN 0 .. v_recipient_count - 1 LOOP
        v_uid := p_recipient_ids[v_idx + 1];
        v_amt := v_share + CASE WHEN v_idx = 0 THEN v_remainder ELSE 0 END;

        IF v_amt > 0 THEN
            INSERT INTO economy (user_id, guild_id, balance)
            VALUES (v_uid::TEXT, p_guild_id, v_amt)
            ON CONFLICT (user_id, guild_id) DO UPDATE
                SET balance = economy.balance + v_amt;

            v_credit_json := v_credit_json || jsonb_build_object('user_id', v_uid, 'amount', v_amt);
        END IF;
    END LOOP;

    -- Write ledger entries
    -- Treasury payment (debit)
    INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, metadata, created_at)
    VALUES (p_guild_id, NULL, p_actor_id, 'treasury_payment', -p_amount, p_reason, to_jsonb(p_recipient_ids), EXTRACT(EPOCH FROM NOW())::BIGINT);

    -- Individual payouts
    FOR v_idx IN 0 .. v_recipient_count - 1 LOOP
        v_uid := p_recipient_ids[v_idx + 1];
        v_amt := v_share + CASE WHEN v_idx = 0 THEN v_remainder ELSE 0 END;

        IF v_amt > 0 THEN
            INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
            VALUES (p_guild_id, v_uid::TEXT, p_actor_id, 'treasury_payout', v_amt, p_reason, EXTRACT(EPOCH FROM NOW())::BIGINT);
        END IF;
    END LOOP;

    -- Record completion
    UPDATE treasury_payments
    SET treasury_after = v_treasury_after,
        credits = v_credit_json
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_treasury_after, v_credit_json;
END;
$$;

REVOKE ALL ON FUNCTION treasury_pay_once(TEXT, TEXT, TEXT, BIGINT, BIGINT[], TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION treasury_pay_once(TEXT, TEXT, TEXT, BIGINT, BIGINT[], TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
-- ============ END: Atomic treasury payments ============

