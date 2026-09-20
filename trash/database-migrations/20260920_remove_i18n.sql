-- Aether is Mongolian-only.  The former per-guild language preference is no
-- longer read by runtime code, so remove the unused column.
ALTER TABLE IF EXISTS public.guild_config DROP COLUMN IF EXISTS lang;
NOTIFY pgrst, 'reload schema';
