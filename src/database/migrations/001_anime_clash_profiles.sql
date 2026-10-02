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
