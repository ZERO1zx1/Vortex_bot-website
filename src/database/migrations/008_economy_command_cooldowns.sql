-- Persistent per-user command cooldowns.
--
-- The money-faucet and rate-limit cooldowns (crime, rob, hack) were kept in
-- process memory, so restarting the bot re-armed every one of them.  Store
-- the last-used timestamps on the economy row instead, next to last_daily and
-- last_work, so the rate limit survives a restart and applies across shards.
--
-- The values are UNIX epoch seconds.  NULL means "never used".
ALTER TABLE public.economy
    ADD COLUMN IF NOT EXISTS last_crime BIGINT,
    ADD COLUMN IF NOT EXISTS last_rob BIGINT,
    ADD COLUMN IF NOT EXISTS last_hack BIGINT,
    ADD COLUMN IF NOT EXISTS last_give BIGINT;
