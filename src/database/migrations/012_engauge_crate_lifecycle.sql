-- Engauge-style XP crate lifecycle: redemption window, cooldown, and
-- optional maximum redeemers per drop.
ALTER TABLE leveling_config
    ADD COLUMN IF NOT EXISTS xp_drop_redeem_seconds INT NOT NULL DEFAULT 300,
    ADD COLUMN IF NOT EXISTS xp_drop_cooldown INT NOT NULL DEFAULT 60,
    ADD COLUMN IF NOT EXISTS xp_drop_max_redeemers INT NOT NULL DEFAULT 0;
