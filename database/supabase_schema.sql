-- Economy
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

-- Levels
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

-- Leveling Config
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

-- Level Roles & Rewards
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

-- Warnings
CREATE TABLE IF NOT EXISTS warnings (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    guild_id TEXT,
    moderator_id TEXT,
    reason TEXT,
    timestamp BIGINT
);

-- Marriages
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

-- Temp Channels
CREATE TABLE IF NOT EXISTS temp_channels (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    owner_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Guild Config
CREATE TABLE IF NOT EXISTS guild_config (
    guild_id TEXT PRIMARY KEY,
    create_channel_id BIGINT,
    max_channels_per_user INT DEFAULT 3,
    category_id BIGINT,
    control_channel_id BIGINT
);

-- Lottery
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

-- Staff Tables (from moderation.py)
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
    stats_channel BIGINT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_economy_balance ON economy (balance);
CREATE INDEX IF NOT EXISTS idx_economy_guild ON economy (guild_id, balance);
CREATE INDEX IF NOT EXISTS idx_levels_guild ON levels (guild_id, level DESC, xp DESC);
