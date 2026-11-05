# Aether project structure

## Directory map

```text
.
├── src/                         # Importable bot runtime
│   ├── main.py                  # Canonical entry point: python -m src.main
│   ├── config.json              # Non-secret bot defaults
│   ├── cogs/                    # Active extensions, grouped by domain
│   │   ├── README.md            # Domain ownership and placement rules
│   │   ├── admin/               # Staff, moderation, automod, webhooks
│   │   ├── community/           # Confessions, greetings, marriage, tickets
│   │   ├── economy/             # Economy, government, leaderboard
│   │   ├── games/               # Games, casino, leveling, PvP, counting
│   │   ├── shop/                # Shop, carts, cafe, player trading
│   │   └── system/              # Help, menu, presence
│   ├── core/                    # Config, logging, errors
│   ├── database/migrations/     # 000 bootstrap; 001+ ordered upgrades
│   ├── ui/                      # Discord presentation and setup-panel UX
│   │   └── setup/               # Shared status/layout/timeout contract
│   └── utils/                   # Shared bot helpers
├── assets/
│   ├── fonts/                   # Runtime fonts, including levelfont.otf
│   ├── images/                  # Card overlays and masks
│   └── gifs/                    # Categorized action assets
├── website/                     # Independently deployed static site
│   ├── index.html
│   ├── css/ and js/             # Browser-facing files
│   └── tools/                   # Catalog generation and validation
├── tools/                       # Reusable development/operations helpers
├── tests/                       # Test source; not a runtime dependency
├── docs/                        # Architecture, deployment and dated reports
├── trash/                       # Retired source and historical migrations
├── .github/workflows/           # Validation and website deployment
└── main.py                      # Compatibility shim; no business logic
```

## Runtime services

- `src/` — Discord bot runtime.
  - `src/main.py` — bot startup, cog loading, command sync, global errors.
  - `src/cogs/` — command and event modules grouped into domain packages.
  - `src/core/` — configuration, exceptions, logging.
  - `src/database/` — Supabase manager and ordered migrations.
  - `src/ui/` — reusable Discord views and presentation rules; no feature DB logic.
  - `src/utils/` — embeds, fonts, asset paths, caches, loaders.
- `website/` — static frontend deployed to Firebase Hosting; reads the public
  `bot_status` heartbeat row directly through the Supabase publishable key.

## Supporting files

- `assets/images/` — image-card overlays and masks.
- `assets/fonts/` — bundled `levelfont.otf`, optional fonts and package metadata.
- `assets/gifs/` — categorized fun-command GIF assets.
- `tests/` — offline unit/regression tests.
- `tools/` — reusable smoke tests, migration probes, and audit helpers.
- `website/tools/` — website command catalog generation and validation.
- `trash/` — deliberately retired cogs, utilities, tools and historical SQL;
  never imported by runtime or replayed as current migrations.
- `docs/` — audit reports, deployment notes, database/security documentation.
- `.github/workflows/` — Python validation and Firebase website deployment.

## Placement rules

1. Bot business logic belongs in the matching `src/cogs/<domain>/` package or
   reusable services, not in `website/` or deployment scripts. Related cogs
   stay together; the `src/cogs/` root contains package metadata only.
2. Discord UI composition belongs in `src/ui/`; generic non-UI helpers such as
   fonts, caches, loaders and low-level embed utilities belong in `src/utils/`.
   Feature database writes remain in the owning cog even when its panel uses a
   shared UI builder.
3. Database schema changes belong in an ordered numeric migration under
   `src/database/migrations/` and in `000_aether_complete.sql` for fresh installs.
   Document upgrade ordering in that directory's README. Historical SQL stays
   in `trash/database-migrations/`.
4. Runtime image assets belong in `assets/images/`; font files belong in
   `assets/fonts/`; fun GIFs belong in categorized `assets/gifs/<action>/`.
5. Generated caches, Python bytecode, npm dependencies, secrets, and local
   logs must remain ignored and must not be committed.
6. The bot and static website remain independently deployable services.
7. Website development scripts belong in `website/tools/` and are excluded
   from Firebase deployment. Generic diagnostics belong in root `tools/`.
8. Use `src.utils.cog_loader.ACTIVE_COGS` as the active feature manifest;
   retired source under `trash/` is not an active feature.

## Setup-panel information order

Administrative setup views share the contract in `src/ui/setup/` and present
information in this order:

1. current state — ready, incomplete, disabled, or draft;
2. required channels, roles, and values;
3. optional rules and secondary settings;
4. one explicit next action;
5. buttons whose labels describe the action they will perform.

The shared layer owns presentation, confirmation, toggle-label, and timeout
behaviour only. Database access and feature decisions remain in the owning cog.

## Current structure status

- Fonts live in `assets/fonts/`; images live in `assets/images/`. Font helpers
  retain legacy-path fallbacks for existing installations.
- The website deploy workflow watches `website/**`, `firebase.json` and
  `.firebaserc` on pushes to `main`.
- Railway currently hosts the bot service; a new deployment is required for
  uncommitted runtime changes to become active.
