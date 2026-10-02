# Archived items

This folder is a recoverable holding area for bot files that have been
explicitly retired from the active Aether feature set.  Nothing is deleted
from here automatically.

## Archiving rules

- Move a file here only after its replacement is working and tested.
- Keep the original relative path under `trash/` when possible.
- Record the reason and date of each move below.

## Archive log

| Date | Original path | Reason |
| --- | --- | --- |
| 2026-09-18 | src/cogs/announcement.py | Replaced by Discord-native automation. |
| 2026-09-18 | src/cogs/avatar_check.py | Not in selected product scope. |
| 2026-09-18 | src/cogs/cafe.py | Legacy economy add-on. |
| 2026-09-18 | src/cogs/invite_tracker.py | Not in selected product scope. |
| 2026-09-18 | src/cogs/lang.py | Retired with Mongolian-only runtime. |
| 2026-09-18 | src/cogs/mafia.py | Legacy game mode. |
| 2026-09-18 | src/cogs/quests.py | Legacy cross-feature progression. |
| 2026-09-18 | src/cogs/reaction_roles.py | Replaced by Discord-native. |
| 2026-09-18 | src/cogs/roles.py | Legacy role utility. |
| 2026-09-18 | src/cogs/stick.py | Legacy social utility. |
| 2026-09-18 | src/cogs/stock.py | Legacy shop/economy add-on. |
| 2026-09-18 | src/cogs/tempvoice.py | Legacy voice utility. |
| 2026-09-18 | src/utils/i18n.py | i18n support removed. |
| 2026-09-20 | tools/expand_i18n_dict.py | i18n helper retired. |
| 2026-09-14 | src/database/migrations/*.sql | Historical repair migrations (superseded by 000_aether_complete.sql). |
