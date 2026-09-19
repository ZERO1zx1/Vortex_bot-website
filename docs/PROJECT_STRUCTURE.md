# Aether project structure

## Runtime services

- `src/` — Discord bot runtime.
  - `src/main.py` — bot startup, cog loading, command sync, global errors.
  - `src/cogs/` — command and event modules.
  - `src/core/` — configuration, exceptions, logging.
  - `src/database/` — Supabase manager, schema, ordered migrations.
  - `src/utils/` — embeds, fonts, asset paths, caches, i18n, loaders.
- `backend/` — independent FastAPI read-only website API.
- `website/` — static frontend deployed to Firebase Hosting.

## Supporting files

- `assets/images/` — image-card overlays, masks, and level font asset.
- `assets/fonts/` — font package metadata and optional bundled fonts.
- `assets/gifs/` — categorized fun-command GIF assets.
- `tests/` — offline unit/regression tests.
- `tools/` — smoke tests, catalog checks, migration probes, and audit helpers.
- `docs/` — audit reports, deployment notes, database/security documentation.
- `.github/workflows/` — Firebase website deployment automation.

## Placement rules

1. Bot business logic belongs in `src/cogs/` or reusable services, not in
   `website/` or deployment scripts.
2. Shared response/embed/font behavior belongs in `src/utils/`.
3. Database schema changes belong in a dated migration under
   `src/database/migrations/` and must be reflected in the schema documentation.
4. Runtime image assets belong in `assets/images/`; font files belong in
   `assets/fonts/`; fun GIFs belong in categorized `assets/gifs/<action>/`.
5. Generated caches, Python bytecode, npm dependencies, secrets, and local
   logs must remain ignored and must not be committed.
6. Bot and backend remain independently deployable services.

## Current structure status

- Asset paths were updated to support the current `assets/images/` layout.
- The website deploy workflow watches `website/**` on pushes to `main`.
- Railway currently hosts the bot service; a new deployment is required for
  uncommitted runtime changes to become active.
