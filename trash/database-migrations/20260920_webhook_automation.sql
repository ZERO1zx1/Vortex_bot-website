-- Safe Discord-native automation rules.  These rules send through the bot to
-- a channel selected by an administrator; arbitrary external webhook URLs are
-- deliberately not stored or called.
CREATE TABLE IF NOT EXISTS automation_rules (
    id BIGSERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    event_name TEXT NOT NULL CHECK (event_name IN ('member_join', 'member_leave')),
    channel_id BIGINT NOT NULL,
    message_template TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_by TEXT NOT NULL,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    UNIQUE (guild_id, event_name)
);

CREATE TABLE IF NOT EXISTS automation_runs (
    id BIGSERIAL PRIMARY KEY,
    rule_id BIGINT NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    guild_id TEXT NOT NULL,
    event_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('sent', 'skipped', 'failed')),
    detail TEXT,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE INDEX IF NOT EXISTS idx_automation_rules_guild ON automation_rules(guild_id);
CREATE INDEX IF NOT EXISTS idx_automation_runs_rule_created ON automation_runs(rule_id, created_at DESC);

ALTER TABLE automation_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON automation_rules, automation_runs FROM anon, authenticated;
GRANT ALL ON automation_rules, automation_runs TO service_role;
GRANT USAGE, SELECT ON SEQUENCE automation_rules_id_seq, automation_runs_id_seq TO service_role;
NOTIFY pgrst, 'reload schema';
