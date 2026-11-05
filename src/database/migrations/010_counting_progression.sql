-- Counting progression: separate spendable XP, lifetime level progress,
-- consumable saves, weekly shields, anti-farm history, and level roles.

ALTER TABLE counting_stats
    ADD COLUMN IF NOT EXISTS xp_balance BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS lifetime_xp BIGINT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS level INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS save_tokens INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_xp_at BIGINT,
    ADD COLUMN IF NOT EXISTS shield_used_at BIGINT;

ALTER TABLE counting_progress
    ADD COLUMN IF NOT EXISTS recent_users JSONB NOT NULL DEFAULT '[]'::JSONB;

ALTER TABLE counting_config
    ADD COLUMN IF NOT EXISTS level_5_role_id BIGINT,
    ADD COLUMN IF NOT EXISTS level_20_role_id BIGINT,
    ADD COLUMN IF NOT EXISTS level_50_role_id BIGINT;

ALTER TABLE counting_stats
    DROP CONSTRAINT IF EXISTS counting_stats_xp_balance_nonnegative,
    DROP CONSTRAINT IF EXISTS counting_stats_lifetime_xp_nonnegative,
    DROP CONSTRAINT IF EXISTS counting_stats_save_tokens_nonnegative;

ALTER TABLE counting_stats
    ADD CONSTRAINT counting_stats_xp_balance_nonnegative CHECK (xp_balance >= 0),
    ADD CONSTRAINT counting_stats_lifetime_xp_nonnegative CHECK (lifetime_xp >= 0),
    ADD CONSTRAINT counting_stats_save_tokens_nonnegative CHECK (save_tokens >= 0);

NOTIFY pgrst, 'reload schema';
