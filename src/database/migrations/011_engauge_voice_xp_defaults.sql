-- Align voice XP with Engauge-style audibility rules.
-- Existing legacy defaults (5 silent / 15 talking) are migrated to 0 / 4.
ALTER TABLE leveling_config
    ALTER COLUMN xp_voice_talking SET DEFAULT 4;

UPDATE leveling_config
SET xp_voice_talking = 4
WHERE xp_voice_talking = 15;
