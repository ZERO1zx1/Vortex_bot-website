# Cog domain map

`src/cogs/` is grouped by product domain. The root only contains package
metadata and this ownership guide; active feature modules live in one of the
folders below.

| Folder | Owns | Examples |
| --- | --- | --- |
| `admin/` | Server safety and staff-only operations | moderation, automod, audit/automation, leveling administration |
| `community/` | Member interaction and community workflows | confessions, greetings, giveaway, marriage, tickets |
| `economy/` | Currency policy, government and rankings | balances, work, government, tax, leaderboard |
| `games/` | Playable activities and progression engines | casino, counting, leveling, PvP, poker |
| `shop/` | Catalogues and player-to-player commerce | shop, carts, cafe, trade |
| `system/` | Bot-wide navigation and runtime presence | help, menu, presence |

## Module boundaries

- A command, listener, and its feature-specific database calls stay in the
  same domain module until the feature needs a dedicated service/repository.
- Reusable Discord panel layout and interaction behaviour belongs in
  `src/ui/`. A cog may import UI helpers; `src/ui/` must not import a cog.
- General non-visual helpers belong in `src/utils/`; configuration and startup
  infrastructure belong in `src/core/`.
- New schema work goes through `src/database/migrations/`, never inside a cog.
- Retired experiments stay under `trash/` and are never loaded as extensions.

## Adding a feature

1. Choose the domain based on who owns the behaviour, not the command name.
2. Add the module to `src.utils.cog_loader.ACTIVE_COGS`.
3. Keep setup-panel presentation consistent with `src.ui.setup`.
4. Add focused tests under `tests/` and run the cog coverage check.
