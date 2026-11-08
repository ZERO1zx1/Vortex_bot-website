-- Engauge-compatible per-server message XP. The default remains 15.
ALTER TABLE leveling_config
    ADD COLUMN IF NOT EXISTS xp_message INT NOT NULL DEFAULT 15;
