-- Remove Aether-only level sources. Engauge progression uses messages, audible
-- voice, configurable crates, and explicit admin actions only.
ALTER TABLE leveling_config
    DROP COLUMN IF EXISTS xp_tiers,
    DROP COLUMN IF EXISTS xp_media,
    DROP COLUMN IF EXISTS xp_reaction,
    DROP COLUMN IF EXISTS xp_voice_silent,
    DROP COLUMN IF EXISTS react_cooldown,
    DROP COLUMN IF EXISTS cafe_buff_enabled,
    DROP COLUMN IF EXISTS invite_xp,
    DROP COLUMN IF EXISTS marriage_bonus;

ALTER TABLE levels
    DROP COLUMN IF EXISTS reaction_count;
