-- Aether core rebuild: private support-ticket foundation.
CREATE TABLE IF NOT EXISTS ticket_config (
    guild_id TEXT PRIMARY KEY,
    category_id BIGINT,
    staff_role_id BIGINT,
    log_channel_id BIGINT,
    panel_channel_id BIGINT,
    panel_message_id BIGINT,
    updated_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW())
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    channel_id BIGINT NOT NULL UNIQUE,
    opener_id TEXT NOT NULL,
    subject TEXT,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    claimed_by TEXT,
    created_at BIGINT NOT NULL DEFAULT EXTRACT(EPOCH FROM NOW()),
    closed_at BIGINT,
    closed_by TEXT
);
CREATE INDEX IF NOT EXISTS ix_tickets_guild_status ON tickets (guild_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_tickets_opener_status ON tickets (guild_id, opener_id, status);

GRANT SELECT, INSERT, UPDATE, DELETE ON ticket_config, tickets TO service_role;
GRANT USAGE, SELECT ON SEQUENCE tickets_id_seq TO service_role;
ALTER TABLE ticket_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ticket_config, tickets FROM anon, authenticated;
NOTIFY pgrst, 'reload schema';
