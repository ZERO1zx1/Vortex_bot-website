-- Engauge-style role stacking and optional stacking groups.
ALTER TABLE level_roles
    ADD COLUMN IF NOT EXISTS stacking BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS stacking_group TEXT;

UPDATE level_roles
SET stacking = TRUE
WHERE stacking IS NULL;
