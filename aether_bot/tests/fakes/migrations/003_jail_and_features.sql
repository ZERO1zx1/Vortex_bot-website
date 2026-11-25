-- ════════════════════════════════════════════════════════════════════════
-- AETHER — migration 003: jail system, guild log channel & lottery pool
--
-- 001 болон 002 нь SHA-256 checksum-тай тул хөндөхгүй. Бүх шинэ багана,
-- хүснэгтийг зөвхөн энэ файлаар нэмнэ.
-- ════════════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = ON;

BEGIN;

-- ── Jail ────────────────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN jail_until TEXT;
ALTER TABLE users ADD COLUMN jail_bail_cost INTEGER NOT NULL DEFAULT 0
    CHECK (jail_bail_cost >= 0);

CREATE INDEX IF NOT EXISTS idx_users_jail ON users(jail_until);

-- ── Guild log channel ───────────────────────────────────────────────────
ALTER TABLE guild_settings ADD COLUMN log_channel_id INTEGER;

-- ── Lottery ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS lottery_tickets (
    ticket_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    round_id        INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_lottery_round
    ON lottery_tickets(round_id, user_id);
CREATE INDEX IF NOT EXISTS idx_lottery_user
    ON lottery_tickets(user_id, created_at DESC);

COMMIT;
