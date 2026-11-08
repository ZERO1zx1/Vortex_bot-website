-- Engauge role XP multipliers are independent from level-role rewards.
CREATE TABLE IF NOT EXISTS level_role_xp_multipliers (
    guild_id TEXT,
    role_id BIGINT,
    multiplier FLOAT NOT NULL DEFAULT 1,
    PRIMARY KEY (guild_id, role_id)
);

UPDATE level_role_xp_multipliers
SET multiplier = 1
WHERE multiplier IS NULL OR multiplier < 0;

-- Clean up the short-lived compatibility column from an earlier draft.
ALTER TABLE level_roles
    DROP COLUMN IF EXISTS xp_multiplier;

