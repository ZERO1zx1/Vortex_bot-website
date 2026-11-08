-- Engauge role reward requirements and role-specific level messages.
ALTER TABLE level_roles
    ADD COLUMN IF NOT EXISTS required_role_ids TEXT DEFAULT '[]',
    ADD COLUMN IF NOT EXISTS level_message TEXT;

UPDATE level_roles
SET required_role_ids = '[]'
WHERE required_role_ids IS NULL;
