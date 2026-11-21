# Aether Discord Bot

Anime / cyber-fantasy RPG & economy bot for Discord, written in Python 3.13 with
`discord.py`, `aiosqlite`, and a layered service architecture.

> **Status:** the infrastructure and skill-tree slice are implemented and
> tested. Economy, shop, casino, and game services are the next stage. The bot
> currently ships `ping`, `balance`, `skills`, `upgrade`, `activate`,
> `setprefix`, and `settings`.

## Requirements

- Python 3.13+
- A Discord application with a bot token
- `Message Content` privileged intent enabled in the Discord Developer Portal
  (needed for prefix commands)

## Setup

```bash
cd aether_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env
# edit .env and set DISCORD_TOKEN and (optionally) GUILD_ID
python bot.py
```

For development, set `GUILD_ID` to your test server ID so slash commands sync
instantly. Without it, commands sync globally and can take up to an hour to
appear.

### Environment variables

| Variable | Default | Notes |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | — | Required to start the bot |
| `GUILD_ID` | `0` | `0` = global slash-command sync |
| `AETHER_DB_PATH` | `data/aether.db` | Relative paths are anchored to `aether_bot/` |
| `RATE_LIMIT_PER_SECOND` | `45` | Clamped to 1–45; Discord's global limit is 50/s |
| `DEFAULT_PREFIX` | `a!` | 1–5 characters |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |

## Commands

Both prefix and slash forms are available through hybrid commands.

| Command | Description |
| :--- | :--- |
| `a!ping` / `/ping` | Gateway latency |
| `a!balance [@user]` / `/balance [member]` | Wallet, bank, level, SP, title |
| `a!skills` / `/skills` | Skill tree and cooldowns |
| `a!upgrade <skill_id>` / `/upgrade <skill_id>` | Spend 1 SP to level a skill |
| `a!activate <skill_id>` / `/activate <skill_id>` | Activate an active skill |
| `a!setprefix <prefix>` / `/setprefix <prefix>` | Change the server prefix (Manage Server) |
| `a!settings` / `/settings` | Show server prefix and tax |

Valid skill IDs are defined in `core/skill_catalog.py`:
`golden_touch`, `lucky_star`, `merchants_eye`, `shadow_step`,
`critical_strike`, `astral_resonance`, `aether_shield`.

## Layout

```text
aether_bot/
├── bot.py              # entry point, DB + cogs + HTTP guard
├── config.py           # typed env parsing, colours, balance constants
├── migrations/         # ordered SQL migrations with checksums
├── core/               # database, locks, rate limiter, event bus, exceptions
├── repositories/       # SQL only
├── services/rpg/       # domain logic (no discord imports)
├── ui/                 # embeds and future views
├── cogs/               # Discord command layer
└── tests/              # pytest + pytest-asyncio
```

Dependency direction: `cogs/ → ui/ → services/ → repositories/ → core/`.

## Development checks

```bash
python -m compileall -q . -x '^\./\.venv'
ruff format --check .
ruff check .
mypy --ignore-missing-imports core utils services repositories ui cogs bot.py config.py tests
pytest -q -W error
```

The CI workflow runs exactly these checks.

## Database and migrations

SQLite runs in WAL mode with foreign keys enabled. Every money-moving service
takes a per-user lock and a `BEGIN IMMEDIATE` transaction. Reads use a separate
`query_only` connection so one task's rollback cannot erase another task's
writes.

Migrations are ordered files in `migrations/`:

- `001_baseline.sql` — schema + initial shop seed
- `002_hardening.sql` — expanded CHECK constraints, append-only financial
  logs, `guild_settings`, expiry indexes

The runner stores each file's SHA-256 in `schema_migrations`. **Never edit an
applied migration**; add a new `NNN_description.sql` instead. A checksum
mismatch fails startup with a clear error.

## Security

- `.env` and database files are git-ignored.
- If a real token or password was ever committed, rotate it in the Discord /
  database console, then purge history with `git filter-repo` or BFG. Removing
  the file in a later commit does not invalidate the leaked credential.
