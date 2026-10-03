# 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹 Discord Bot

A feature-rich Discord bot for the **𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹** community, built with `discord.py` and **Supabase** (PostgreSQL) as the database backend.

## Features

- **Economy** — balance, bank, daily, work, jobs, hunger/mood, prison
- **Leveling** — XP, ranks, level roles, level rewards, voice XP, XP drops, rank cards
- **Marriage & Family** — proposals, divorce, adoption, family tree cards, love points, gifts
- **Games & Casino** — Anime Clash, multiplayer Texas Hold'em, slots, blackjack, PvP, lottery
- **Shop & Inventory** — items, stock, marketplace, food buffs (cafe)
- **Moderation** — warnings, temproles, sticky messages, avatar logging
- **Counting** — counting game with configurable channels, roles, streaks
- **Confessions** — anonymous confessions with blacklist & cooldown
- **Giveaways** — hosted giveaways with entries & winners
- **Greetings** — customizable welcome/goodbye/boost embeds with templates
- **Leaderboards** — level, messages, voice, reactions, money, invites, counting, games

Active features are defined in `src/utils/cog_loader.py` (`ACTIVE_COGS`). Retired
invite-tracking, temp-voice, quests and mafia cogs remain in `trash/`; they are
not registered at startup.

## Tech Stack

- **Python 3.10+**
- **discord.py 2.3+**
- **Supabase** (PostgreSQL + PostgREST)
- **Pillow** for image generation (rank cards, family trees, leaderboard cards)

## Project Structure

```
.
├── main.py                        # Deploy shim → re-invokes src.main (Railway legacy start cmd)
├── src/
│   ├── main.py                    # Bot entry point, cog loading, error handlers
│   ├── config.json                # Bot configuration (prefix, owner, co-owners)
│   ├── core/                      # config loader, logging setup, exceptions
│   ├── database/
│   │   ├── db_manager.py          # Async Supabase repository layer (retry + error classify)
│   │   └── migrations/            # Supabase bootstrap + incremental migrations
│   ├── utils/                     # branding, embeds, fonts, caches, cog loader
│   └── cogs/                      # 28 active feature modules (manifest + discovery)
├── assets/                        # fonts/, images/, gifs/ (separate asset types)
├── website/                       # Static marketing site (Firebase Hosting)
│   ├── index.html, css/, js/      # config.js = single place for links/keys
│   └── tools/                     # Website-specific sync scripts (commands, i18n)
├── tools/                         # Dev/ops scripts (offline probes, smoke tests, migrations)
├── tests/                         # pytest unit tests (offline, no Discord/Supabase)
├── docs/                          # Audit & repair reports, production hardening notes
├── trash/                         # Retired source, tools and historical SQL (not runtime)
├── requirements.txt
├── .env.example                   # Environment template (copy to .env)
├── Dockerfile / railway.json      # Container deploy (Railway: python -m src.main)
└── firebase.json / .firebaserc    # Website hosting deploy
```

See [the structure guide](docs/PROJECT_STRUCTURE.md) for ownership and placement rules.

House rules:

- **Runtime Python код** `src/` package дотор; root-д зөвхөн `main.py` shim.
  Test source нь `tests/`, reusable diagnostics нь `tools/`, website tooling нь
  `website/tools/` дотор байна.
- **Нэг удаагийн codemod/миграц скрипт** ажилласныхаа дараа `tools/`-ээс устгана
  эсвэл `docs/`-д тайлан болгон архивлана — `tools/` зөвхөн дахин хэрэглэгдэх
  probe/smoke/sync скриптүүдийг хадгална.
- **Generated зүйлс** (`__pycache__/`, `.pytest_cache/`, `.firebase/`, `logs/`,
  `.ruff_cache/`, `.uv-cache/`, `.agentcore/`) хэзээ ч commit хийхгүй — `.gitignore`-д бүртгэлтэй.
- **AgentCore audit** (сонголтоор): `python tools/agentcore_audit.py . --mode FULL`
  — repo-г real deterministic шалгалтаар (pytest/compileall/node + бүтцийн
  hygiene) үнэлж, `.agentcore/` дотор checkpoint + artifact + тайлан үлдээнэ.

## Setup

### 1. Install dependencies

```bash
# Windows: use the same Python interpreter that will run the bot
py -3.12 -m pip install -r requirements.txt
# Or, if `python` is your selected interpreter:
python -m pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `DISCORD_TOKEN` — your bot token
- `SUPABASE_URL` / `SUPABASE_SECRET_KEY` — server-only Supabase credentials (`SUPABASE_SERVICE_ROLE_KEY` and legacy `SUPABASE_KEY` remain supported during migration)
- `OWNER_ID` / `CO_OWNERS` — your Discord user IDs
- `GUILD_ID` — server ID for immediate slash-command sync (multiple IDs may be comma-separated)

### 3. Configure Discord

In the [Discord Developer Portal](https://discord.com/developers/applications), open the bot application and enable the privileged Gateway intents it uses:

- **Message Content Intent** — required for prefix commands and message-based features.
- **Server Members Intent** — required for member, invite, and moderation features.
- **Presence Intent** — required for presence-aware features.

Also invite the bot with both the `bot` and `applications.commands` OAuth2 scopes. Guild command sync is immediate and is useful for testing; global commands are the production scope and Discord refreshes stale command definitions when a user invokes one.

### 4. Set up the database

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Open the **SQL Editor**
3. Paste the contents of `src/database/migrations/000_aether_complete.sql` and run it
4. For an existing project, also apply the unapplied incremental migrations in order:
   `001_anime_clash_profiles.sql`, `002_poker_pending_payouts.sql`,
   `003_economy_balance_idempotency.sql`, `004_confession_atomic_ids.sql`,
   `005_economy_tax_atomic.sql`, and `006_treasury_atomic.sql`.
5. Restart the bot and confirm the startup log reports a successful database health check. The migrations are designed to be applied in order without dropping existing data.

### 5. Configure the bot

Edit `src/config.json`:

```json
{
  "prefix": "!",
  "owner_id": "your_discord_id",
  "co_owner_ids": []
}
```

### 6. Run the bot

```bash
# From the repository root. The src/ package is importable either way:
py -3.12 -m src.main
# Or:
python -m src.main
```

If you see `ModuleNotFoundError: No module named 'discord'`, install dependencies with the exact interpreter used to run the bot:

```bash
py -3.12 -m pip install -r requirements.txt
```

## Database Layer

All cogs use the async repository layer in `src/database/db_manager.py`:

```python
# Fetch a single row
row = await self.bot.db_manager.fetch_one("economy", {"user_id": "123", "guild_id": "456"})

# Fetch multiple rows (with ordering/pagination)
rows = await self.bot.db_manager.fetch_all("levels", {"guild_id": "456"}, order_by="level", desc=True, limit=10, offset=0)

# Insert
await self.bot.db_manager.insert("marriages", {...})

# Update
await self.bot.db_manager.update("economy", {"user_id": "123"}, {"balance": 5000})

# Upsert (insert or update on conflict)
await self.bot.db_manager.upsert("leveling_config", {...}, on_conflict="guild_id")

# Delete
await self.bot.db_manager.delete("warnings", {"id": 42})

# Atomic increment
await self.bot.db_manager.increment("economy", {"user_id": "123"}, "balance", 100)
```

## Website

`website/` хавтас — ботын албан ёсны статик UI. Командын каталог болон live status нь тусдаа FastAPI service шаардахгүй; status нь зөвхөн нийтэд унших эрхтэй `bot_status` мөрийг Supabase publishable key-ээр уншина.

- Hero (3D orb + particles), Онцлогууд, командын каталог, Статистик, Статус, About Us, Premium (3 төлөвлөгөө), Invite CTA
- Hosting: Vercel / Netlify / GitHub Pages дээр `website/` хавтсыг publish directory болгох (нарийвчилсан заавар: `website/README.md`)
- Тохиргоо: `website/js/config.js`-с invite холбоосоо тохируулна (`INVITE_URL`)
## Branding

All embeds and UI use the centralized branding layer in `src/utils/branding.py`:

```python
from src.utils.branding import BOT_NAME, BOT_ICON_URL, PRIMARY_COLOR, footer_text
from src.utils.embeds import success_embed, error_embed, info_embed
```

## License

MIT
