-- Configurable Engauge-style level and crate announcement messages.
ALTER TABLE leveling_config
    ADD COLUMN IF NOT EXISTS level_message TEXT DEFAULT '{mention} Level {level} хүрлээ!',
    ADD COLUMN IF NOT EXISTS xp_drop_message TEXT DEFAULT '🌟 {xp} XP crate drop боллоо!';

UPDATE leveling_config
SET level_message = '{mention} Level {level} хүрлээ!'
WHERE level_message IS NULL;

UPDATE leveling_config
SET xp_drop_message = '🌟 {xp} XP crate drop боллоо!'
WHERE xp_drop_message IS NULL;
