-- Add Engauge-style crate trigger criteria.
ALTER TABLE leveling_config
    ADD COLUMN IF NOT EXISTS xp_drop_criteria TEXT DEFAULT 'time',
    ADD COLUMN IF NOT EXISTS xp_drop_message_count INT DEFAULT 100,
    ADD COLUMN IF NOT EXISTS xp_drop_contributing_channels TEXT DEFAULT '[]';

UPDATE leveling_config
SET xp_drop_criteria = 'time'
WHERE xp_drop_criteria IS NULL
   OR xp_drop_criteria NOT IN ('time', 'message_count', 'manual');

UPDATE leveling_config
SET xp_drop_message_count = 100
WHERE xp_drop_message_count IS NULL OR xp_drop_message_count < 1;

UPDATE leveling_config
SET xp_drop_contributing_channels = '[]'
WHERE xp_drop_contributing_channels IS NULL;
