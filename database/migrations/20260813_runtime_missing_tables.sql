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
    fake INT DEFAULT 0,
    left INT DEFAULT 0,
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
) RETURNS VOID LANGUAGE plpgsql AS $$
BEGIN
    EXECUTE format(
        'UPDATE %I SET %I = COALESCE(%I, 0) + %s WHERE %I = %L',
        table_name, col, col, delta, filter_col, filter_val
    );
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
