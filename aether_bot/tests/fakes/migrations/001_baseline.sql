-- ════════════════════════════════════════════════════════════════════════
-- AETHER — migration 001: baseline schema + initial shop seed
-- WAL + Foreign Keys. Бүх мөнгөн гүйлгээ service давхаргад
-- `BEGIN IMMEDIATE` транзакци + per-user asyncio lock дор хийгдэнэ.
-- ════════════════════════════════════════════════════════════════════════

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

BEGIN;

-- ── Тоглогч ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    wallet          INTEGER NOT NULL DEFAULT 500 CHECK (wallet >= 0),
    bank            INTEGER NOT NULL DEFAULT 0   CHECK (bank >= 0),
    xp              INTEGER NOT NULL DEFAULT 0   CHECK (xp >= 0),
    level           INTEGER NOT NULL DEFAULT 1   CHECK (level >= 1),
    skill_points    INTEGER NOT NULL DEFAULT 0   CHECK (skill_points >= 0),
    daily_streak    INTEGER NOT NULL DEFAULT 0   CHECK (daily_streak >= 0),
    casino_net      INTEGER NOT NULL DEFAULT 0,  -- leaderboard: казиногийн цэвэр ашиг
    last_daily_at   TEXT,
    shield_until    TEXT,                        -- Shop Shield / Aether Shield
    active_title    TEXT NOT NULL DEFAULT 'Wanderer',
    bio             TEXT NOT NULL DEFAULT 'Aether ертөнцийн аялагч.',
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_users_level   ON users(level DESC, xp DESC);
CREATE INDEX IF NOT EXISTS idx_users_wealth  ON users(wallet, bank);
CREATE INDEX IF NOT EXISTS idx_users_casino  ON users(casino_net DESC);

-- ── Skill tree ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_skills (
    user_id         INTEGER NOT NULL,
    skill_id        TEXT    NOT NULL,
    skill_level     INTEGER NOT NULL DEFAULT 0 CHECK (skill_level >= 0),
    last_used_at    TEXT,      -- cooldown-ийн эхлэл
    active_until    TEXT,      -- идэвхтэй эффектийн төгсгөл (NULL = идэвхгүй)
    PRIMARY KEY (user_id, skill_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ── Дэлгүүр ба Inventory ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS shop_items (
    item_id         TEXT PRIMARY KEY,
    name            TEXT    NOT NULL,
    category        TEXT    NOT NULL
                    CHECK (category IN ('defense', 'booster', 'title', 'scroll')),
    price           INTEGER NOT NULL CHECK (price > 0),
    description     TEXT    NOT NULL,
    effect_type     TEXT    NOT NULL,  -- shield / xp_boost / skill_reset / title / stamina
    effect_value    REAL    NOT NULL DEFAULT 0,
    duration_sec    INTEGER NOT NULL DEFAULT 0,
    icon            TEXT    NOT NULL DEFAULT '✦'
);

CREATE TABLE IF NOT EXISTS inventory (
    user_id         INTEGER NOT NULL,
    item_id         TEXT    NOT NULL,
    quantity        INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    PRIMARY KEY (user_id, item_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id)     ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES shop_items(item_id) ON DELETE CASCADE
);

-- Item-ээр олгогдсон түр эффект (XP booster, Shield гэх мэт)
CREATE TABLE IF NOT EXISTS user_effects (
    effect_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    effect_type     TEXT    NOT NULL,
    value           REAL    NOT NULL DEFAULT 0,
    expires_at      TEXT    NOT NULL,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_effects_user ON user_effects(user_id, effect_type);

-- ── Cooldown ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cooldowns (
    user_id         INTEGER NOT NULL,
    action_key      TEXT    NOT NULL,  -- 'work', 'rob', 'adventure', 'xp_chat'
    expires_at      TEXT    NOT NULL,
    PRIMARY KEY (user_id, action_key),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- ── Санхүүгийн бүртгэл (append-only) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    tx_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    amount          INTEGER NOT NULL,               -- + орлого / - зарлага
    source          TEXT    NOT NULL,               -- daily, work, casino_win, ...
    balance_after   INTEGER NOT NULL DEFAULT 0,
    metadata        TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id, created_at DESC);

-- ── Казино ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS casino_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    game            TEXT    NOT NULL CHECK (game IN ('slots', 'blackjack', 'roulette', 'minefield')),
    bet             INTEGER NOT NULL CHECK (bet > 0),
    payout          INTEGER NOT NULL DEFAULT 0,
    outcome         TEXT    NOT NULL CHECK (outcome IN ('win', 'loss', 'push', 'cashout')),
    detail          TEXT,                            -- JSON: reels, cards, multiplier
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_casino_user ON casino_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_casino_game ON casino_logs(game, created_at DESC);

-- ── PvP Duel / Adventure ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS game_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind            TEXT    NOT NULL CHECK (kind IN ('duel', 'adventure')),
    user_id         INTEGER NOT NULL,
    opponent_id     INTEGER,
    outcome         TEXT    NOT NULL CHECK (outcome IN ('win', 'loss', 'draw', 'flee')),
    reward_coin     INTEGER NOT NULL DEFAULT 0,
    reward_xp       INTEGER NOT NULL DEFAULT 0,
    detail          TEXT,                            -- JSON: rounds, item drop
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id)     REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (opponent_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_game_user ON game_logs(user_id, kind, created_at DESC);

-- ── Seed: дэлгүүрийн анхны бараа ────────────────────────────────────────
INSERT OR IGNORE INTO shop_items
    (item_id, name, category, price, description, effect_type, effect_value, duration_sec, icon)
VALUES
    ('aether_shield_charm', 'Aether Shield Charm', 'defense', 1200,
     '6 цагийн турш дээрмээс 100% хамгаална.', 'shield', 1.0, 21600, '🛡️'),
    ('xp_potion_2x', 'Astral XP Elixir', 'booster', 900,
     '30 минутын турш бүх XP-г 2 дахин нэмнэ.', 'xp_boost', 2.0, 1800, '🧪'),
    ('skill_reset_tome', 'Tome of Rebirth', 'scroll', 2500,
     'Бүх skill-ийг буцааж, зарцуулсан SP-г бүрэн буцаана.', 'skill_reset', 0, 0, '📜'),
    ('stamina_elixir', 'Shadowstep Elixir', 'booster', 600,
     'Дараагийн /work болон /rob-ийн cooldown-ыг шууд цэвэрлэнэ.', 'stamina', 1.0, 0, '⚡'),
    ('cyber_ronin_title', 'Cyber Ronin', 'title', 5000,
     'Неон илдтэй тэнүүчлэгч — профайл дээр харагдах цол.', 'title', 0, 0, '⚔️'),
    ('astral_princess_title', 'Astral Princess', 'title', 5000,
     'Оддын хаант улсын өв залгамжлагч — профайл дээр харагдах цол.', 'title', 0, 0, '👑');

COMMIT;
