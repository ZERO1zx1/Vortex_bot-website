-- ════════════════════════════════════════════════════════════════════════
-- AETHER — migration 002: audit hardening
--
-- 1. Expand content CHECK constraints so planned casino/game/shop types
--    do not require another table rebuild.
-- 2. Make financial/audit tables append-only: ON DELETE RESTRICT plus
--    UPDATE/DELETE guard triggers.
-- 3. Add guild_settings for per-guild prefix/tax.
-- 4. Add expiry indexes used by cleanup jobs.
--
-- Existing databases get this automatically because migration 001 is already
-- recorded in schema_migrations. Fresh databases run 001 then 002.
-- ════════════════════════════════════════════════════════════════════════

PRAGMA foreign_keys = OFF;

BEGIN;

-- ── shop_items: allow tool/consumable categories ────────────────────────
CREATE TABLE shop_items_new (
    item_id         TEXT PRIMARY KEY,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL
                    CHECK (category IN ('defense', 'booster', 'title', 'scroll', 'tool', 'consumable')),
    price           INTEGER NOT NULL CHECK (price > 0),
    description     TEXT    NOT NULL,
    effect_type     TEXT    NOT NULL,
    effect_value    REAL    NOT NULL DEFAULT 0,
    duration_sec    INTEGER NOT NULL DEFAULT 0,
    icon            TEXT    NOT NULL DEFAULT '✦'
);
INSERT INTO shop_items_new
    (item_id, name, category, price, description, effect_type, effect_value, duration_sec, icon)
SELECT item_id, name, category, price, description, effect_type, effect_value, duration_sec, icon
  FROM shop_items;
DROP TABLE shop_items;
ALTER TABLE shop_items_new RENAME TO shop_items;

-- ── transactions: append-only ledger ────────────────────────────────────
CREATE TABLE transactions_new (
    tx_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    amount          INTEGER NOT NULL,
    source          TEXT    NOT NULL,
    balance_after   INTEGER NOT NULL DEFAULT 0,
    metadata        TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);
INSERT INTO transactions_new
    (tx_id, user_id, amount, source, balance_after, metadata, created_at)
SELECT tx_id, user_id, amount, source, balance_after, metadata, created_at
  FROM transactions;
DROP TABLE transactions;
ALTER TABLE transactions_new RENAME TO transactions;
CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, created_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_transactions_no_update
BEFORE UPDATE ON transactions
BEGIN
    SELECT RAISE(ABORT, 'transactions append-only: UPDATE хориотой');
END;

CREATE TRIGGER IF NOT EXISTS trg_transactions_no_delete
BEFORE DELETE ON transactions
BEGIN
    SELECT RAISE(ABORT, 'transactions append-only: DELETE хориотой');
END;

-- ── casino_logs: expand game catalog, append-only ───────────────────────
CREATE TABLE casino_logs_new (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    game            TEXT    NOT NULL
                    CHECK (game IN ('slots', 'blackjack', 'roulette', 'minefield',
                                    'coinflip', 'crash', 'lottery')),
    bet             INTEGER NOT NULL CHECK (bet > 0),
    payout          INTEGER NOT NULL DEFAULT 0,
    outcome         TEXT    NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'cashout')),
    detail          TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT
);
INSERT INTO casino_logs_new
    (log_id, user_id, game, bet, payout, outcome, detail, created_at)
SELECT log_id, user_id, game, bet, payout, outcome, detail, created_at
  FROM casino_logs;
DROP TABLE casino_logs;
ALTER TABLE casino_logs_new RENAME TO casino_logs;
CREATE INDEX IF NOT EXISTS idx_casino_user ON casino_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_casino_game ON casino_logs(game, created_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_casino_logs_no_update
BEFORE UPDATE ON casino_logs
BEGIN
    SELECT RAISE(ABORT, 'casino_logs append-only: UPDATE хориотой');
END;

CREATE TRIGGER IF NOT EXISTS trg_casino_logs_no_delete
BEFORE DELETE ON casino_logs
BEGIN
    SELECT RAISE(ABORT, 'casino_logs append-only: DELETE хориотой');
END;

-- ── game_logs: expand game kinds, append-only ───────────────────────────
CREATE TABLE game_logs_new (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT    NOT NULL
                    CHECK (kind IN ('duel', 'adventure', 'hunt', 'fish', 'boss')),
    user_id         INTEGER NOT NULL,
    opponent_id     INTEGER,
    outcome         TEXT    NOT NULL CHECK (outcome IN ('win', 'loss', 'draw', 'flee')),
    reward_coin     INTEGER NOT NULL DEFAULT 0,
    reward_xp       INTEGER NOT NULL DEFAULT 0,
    detail          TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (opponent_id) REFERENCES users(user_id) ON DELETE SET NULL
);
INSERT INTO game_logs_new
    (log_id, kind, user_id, opponent_id, outcome, reward_coin, reward_xp, detail, created_at)
SELECT log_id, kind, user_id, opponent_id, outcome, reward_coin, reward_xp, detail, created_at
  FROM game_logs;
DROP TABLE game_logs;
ALTER TABLE game_logs_new RENAME TO game_logs;
CREATE INDEX IF NOT EXISTS idx_game_user ON game_logs(user_id, kind, created_at DESC);

CREATE TRIGGER IF NOT EXISTS trg_game_logs_no_update
BEFORE UPDATE ON game_logs
BEGIN
    SELECT RAISE(ABORT, 'game_logs append-only: UPDATE хориотой');
END;

CREATE TRIGGER IF NOT EXISTS trg_game_logs_no_delete
BEFORE DELETE ON game_logs
BEGIN
    SELECT RAISE(ABORT, 'game_logs append-only: DELETE хориотой');
END;

-- ── Per-guild settings ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id        INTEGER PRIMARY KEY,
    prefix          TEXT    NOT NULL DEFAULT 'a!'
                    CHECK (length(prefix) BETWEEN 1 AND 5),
    tax_pct         REAL    NOT NULL DEFAULT 0.0
                    CHECK (tax_pct >= 0.0 AND tax_pct <= 0.5),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ── Expiry indexes for cleanup jobs ─────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_effects_expiry ON user_effects(expires_at);
CREATE INDEX IF NOT EXISTS idx_cooldowns_expiry ON cooldowns(expires_at);

COMMIT;

PRAGMA foreign_keys = ON;
