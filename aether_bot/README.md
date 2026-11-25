# Aether Discord Bot

Anime / cyber-fantasy RPG & economy bot for Discord, written in Python 3.13 with
`discord.py`, Supabase PostgreSQL, and a layered service architecture.

> **Status:** the layered infrastructure, economy, jail, RPG, shop, casino,
> games, interactive UI, prefix player commands, and slash-only admin commands
> are implemented and covered by the offline test suite. Live Supabase schema
> validation remains opt-in and requires a disposable database URL.

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
# edit .env and set DISCORD_TOKEN, DATABASE_URL, and optionally GUILD_ID
python bot.py
```

Create a new Supabase project, open **Connect**, select **Session pooler**
(port `5432`), copy its PostgreSQL URL, replace the password placeholder, and
store it as `DATABASE_URL` in `.env`. The password must be URL-encoded when it
contains reserved characters. Never commit or paste the completed URL.

For development, set `GUILD_ID` to your test server ID so slash commands sync
instantly. Without it, commands sync globally and can take up to an hour to
appear.

### Environment variables

| Variable | Default | Notes |
| :--- | :--- | :--- |
| `DISCORD_TOKEN` | — | Required to start the bot |
| `GUILD_ID` | `0` | `0` = global slash-command sync |
| `DATABASE_URL` | — | Required Supabase Session pooler PostgreSQL URL |
| `RATE_LIMIT_PER_SECOND` | `45` | Clamped to 1–45; Discord's global limit is 50/s |
| `DEFAULT_PREFIX` | `a!` | 1–5 characters |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |

## Commands

Player commands are prefix-only. Admin commands are slash-only.

| Group | Commands |
| :--- | :--- |
| System | `a!help`, `a!ping`, `a!settings` |
| Economy | `a!balance`, `a!deposit`, `a!withdraw`, `a!transfer`, `a!daily`, `a!work`, `a!crime`, `a!rob`, `a!jail`, `a!bail` |
| RPG | `a!profile`, `a!rank`, `a!leaderboard`, `a!skills`, `a!upgrade`, `a!activate`, `a!shop`, `a!buy`, `a!inventory`, `a!use`, `a!equip` |
| Casino | `a!slots`, `a!blackjack`, `a!roulette`, `a!minefield`, `a!coinflip`, `a!crash`, `a!lottery` |
| Games | `a!duel`, `a!adventure`, `a!hunt`, `a!fish`, `a!boss` |
| Admin | `/admin_economy`, `/admin_jail`, `/admin_shop`, `/admin_skill`, `/admin_config` |

`a!work`, crime, casino, and game commands reject users who are currently jailed.

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
├── services/           # economy, RPG, casino, and games domain logic
├── ui/                 # embeds, views, buttons, selects, and modals
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

The bot uses an `asyncpg` application pool over Supabase's TLS Session pooler.
Every money-moving service takes a per-user lock and a PostgreSQL transaction;
nested repository calls share the same connection and roll back together.

Migrations are ordered files in `migrations/`:

- `001_baseline.sql` — schema + initial shop seed
The fresh baseline creates all tables, indexes, RLS protection, immutable audit
triggers, and the initial shop catalog.

The runner stores each file's SHA-256 in `schema_migrations`. **Never edit an
applied migration**; add a new `NNN_description.sql` instead. A checksum
mismatch fails startup with a clear error.

## Security

- `.env` and database files are git-ignored.
- Public tables have RLS enabled with no client policies; the bot connects as
  the database role through TLS rather than exposing the password to Discord users.
- If a real token or password was ever committed, rotate it in the Discord /
  database console, then purge history with `git filter-repo` or BFG. Removing
  the file in a later commit does not invalidate the leaked credential.
