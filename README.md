# 𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹 Discord Bot

A feature-rich Discord bot for the **𝓐𝓮𝓽𝓱𝓮𝓻  蒼穹** community, built with `discord.py` and **Supabase** (PostgreSQL) as the database backend.

## Features

- **Economy** — balance, bank, daily, work, jobs, hunger/mood, prison
- **Leveling** — XP, ranks, level roles, level rewards, voice XP, XP drops, rank cards
- **Marriage & Family** — proposals, divorce, adoption, family tree cards, love points, gifts
- **Games & Casino** — slots, blackjack, mines, mafia, PvP, lottery
- **Shop & Inventory** — items, stock, marketplace, food buffs (cafe)
- **Moderation** — warnings, temproles, sticky messages, avatar logging
- **Counting** — counting game with configurable channels, roles, streaks
- **Confessions** — anonymous confessions with blacklist & cooldown
- **Giveaways** — hosted giveaways with entries & winners
- **Invite Tracking** — invite stats, fake detection, labels, daily stats
- **Greetings** — customizable welcome/goodbye/boost embeds with templates
- **Temp Voice** — temporary voice channels with owner controls
- **Quests** — daily/weekly quests with rewards
- **Leaderboards** — level, messages, voice, reactions, money, invites, counting, games

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
│   │   ├── schema.sql             # Original full schema + RPC functions
│   │   └── migrations/            # Versioned SQL migrations (apply newest last)
│   ├── utils/                     # branding, embeds, fonts, i18n, caches, cog loader
│   └── cogs/                      # 36 feature modules (auto-discovered, one per feature)
├── assets/gifs/                   # Action-command GIF sets (hug, kiss, slap, ...)
├── backend/                       # FastAPI status/leaderboard/giveaway API (+ data/commands.json)
├── website/                       # Static marketing site (Firebase Hosting)
│   ├── index.html, css/, js/      # config.js = single place for links/keys
│   └── tools/                     # Website-specific sync scripts (commands, i18n)
├── tools/                         # Dev/ops scripts (offline probes, smoke tests, migrations)
├── tests/                         # pytest unit tests (offline, no Discord/Supabase)
├── docs/                          # Audit & repair reports, production hardening notes
├── requirements.txt
├── .env.example                   # Environment template (copy to .env)
├── Dockerfile / railway.json      # Container deploy (Railway: python -m src.main)
└── firebase.json / .firebaserc    # Website hosting deploy
```

House rules:

- **Бүх Python код** `src/` package дотор; root-д зөвхөн `main.py` shim.
- **Нэг удаагийн codemod/миграц скрипт** ажилласныхаа дараа `tools/`-ээс устгана
  эсвэл `docs/`-д тайлан болгон архивлана — `tools/` зөвхөн дахин хэрэглэгдэх
  probe/smoke/sync скриптүүдийг хадгална.
- **Generated зүйлс** (`__pycache__/`, `.pytest_cache/`, `.firebase/`, `logs/`,
  `.agentcore/`) хэзээ ч commit хийхгүй — `.gitignore`-д бүртгэлтэй.
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

### 3. Set up the database

1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Open the **SQL Editor**
3. Paste the contents of `src/database/migrations/20260101_001_initial_schema.sql` and run it
4. Then apply any later migrations in `src/database/migrations/` (newest last). This creates all tables, indexes, and the `increment()` RPC function without dropping existing data

### 4. Configure the bot

Edit `config.json`:

```json
{
  "prefix": "!",
  "owner_id": "your_discord_id",
  "co_owner_ids": []
}
```

### 5. Run the bot

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

`website/` хавтас — ботын албан ёсны статик UI. Командын каталог зэрэг хэсэг backend-гүй ажиллана; live status нь нууц database key-г browser-т гаргахгүйн тулд `backend/` API шаарддаг.

- Hero (3D orb + particles), Онцлогууд, 201 командын хайлттай жагсаалт, Статистик, Статус, About Us, Premium (3 төлөвлөгөө), Invite CTA
- Hosting: Vercel / Netlify / GitHub Pages дээр `website/` хавтсыг publish directory болгох (нарийвчилсан заавар: `website/README.md`)
- Тохиргоо: `website/js/config.js`-с invite холбоосоо тохируулна (`INVITE_URL`)
## Branding

All embeds and UI use the centralized branding layer in `src/utils/branding.py`:

```python
from utils.branding import BOT_NAME, BOT_ICON_URL, PRIMARY_COLOR, footer_text
from utils.embeds import success_embed, error_embed, info_embed
```

## License

MIT
