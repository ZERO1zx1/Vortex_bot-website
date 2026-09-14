# Aether Bot — Repair Report

Date: 2026-09-14

## 1. Root causes

Production was failing against the Supabase (PostgREST) backend with two errors,
spamming `cogs.log` (39,955 lines, ~2,158 ERRORs):

| Error | Meaning | Source |
|---|---|---|
| PostgreSQL `42501` (permission denied) | `service_role` was not granted read/write on runtime tables | Grants created in migration `000_complete_schema.sql` were never applied |
| PostgREST `PGRST205` (429/404-style "could not find the table") | Tables missing entirely: `staff_members`, `staff_activity`, `warnings`, `game_stats`, `temp_channels`, quest/config tables | Migration `000_complete_schema.sql` was never applied on the production project |

Top noise sources (2,158 ERRORs total): `confession_config` 468x, `counting_config` 468x, `staff_members` 335 missing + 151 denied, `staff_activity`, `temp_channels`, `avatar_log_config`, `work_phrases`, etc.

Secondary bugs found during audit:

- `confessions.get_config` / `counting.get_config` re-fetched DB config **on every message** → 468x/per-event error spam.
- `main.py` used `logger.exception(...)` **outside** an exception context in the command/slash error handlers → spurious `NoneType: None` tracebacks masking real errors.
- `economy.py` used a lazy `__import__("logging")` immediately followed by `.error(...)` → `AttributeError: 'module' object has no attribute 'error'` in a background loop.
- `mines.py` cashout had a race: double invocation by the interaction timeout/fast clicks could reward twice; the `settled` guard could stay `False` after a cashout so a later timeout refunded again.
- `quests.trigger_event` propagated infra exceptions into game/cashout/economy paths.
- `user_equips` table shape in `000_complete_schema.sql` (per-item rows) did not match `shop.py` + `20260824_equip_system.sql` (per-slot rows) — equips wrote to columns that did not exist.
- `on_voice_state_update` in moderation read `staff_members` unguarded → a voice state change could raise.
- `fetch_safe` logged a full traceback for **every** failed table read → per-event log flooding.

## 2. Changes

### Database

- `database/migrations/000_complete_schema.sql`
  - Fixed `user_equips` to slot-based shape matching `shop.py`:
    `(guild_id TEXT, user_id TEXT, slot TEXT, item_id BIGINT, updated_at BIGINT DEFAULT 0, PRIMARY KEY (guild_id, user_id, slot))`.
  - Already the canonical source of all DDL + `service_role` grants (idempotent DO-loop over `pg_tables`, line ~646) + RLS + `NOTIFY pgrst`.
- `database/migrations/20260914_repair_runtime_schema.sql` — **new, idempotent, runnable in the Supabase SQL Editor**:
  - Creates any missing lifecycle-critical tables (`staff_members`, `staff_activity`, `warnings`, `game_stats`, `role_income`, `work_phrases`, `temp_channels`, `tempvoice_setup_msg`, `guild_config`, `counting_config`, `confession_config`, `avatar_log_config`, `invite_log_config`, `greeting_config`, `user_quests`, `quest_history`, …) with `IF NOT EXISTS`.
  - Rebuilds `user_equips` to the slot shape if a legacy column-based shape is detected (moves `slot_*` values to rows).
  - Grants `SELECT, INSERT, UPDATE, DELETE` on **all** public tables + sequences/functions to `service_role` (idempotent).
  - Re-applies RLS, revokes `anon`/`authenticated` access (mirrors `000`), adds `bot_status` anon read policy.
  - Emits `NOTIFY pgrst, 'reload schema'` so Supabase picks up the changes without restart.

### Code

- `database/supabase_manager.py`
  - Typed exceptions: `DatabaseUnavailableError`, `DatabasePermissionError`, `DatabaseSchemaError`.
  - `classify_supabase_error()` maps PGRST205/404 → schema, 42501 → permission, network/5xx → unavailable; unknown errors pass through unchanged (drop-in: `fetch_one`/`fetch_all` raise semantics untouched).
  - `_TableErrorTracker` (10-min window): first failure per table logs full guidance, repeats are silently counted, then a compact `Table 'X' unavailable: N repeat error(s) …` summary — kills the per-event flooding.
  - `fetch_safe` wired to the tracker; `single=True` supported.
  - New `probe_table()` → `OK | MISSING | PERMISSION_DENIED | UNAVAILABLE | ERROR` and `health_check(tables=...)`.
- `utils/config_cache.py` — async TTL cache (per-key `asyncio.Lock` coalescing, LRU maxsize 512, explicit `invalidate()`). Caches falsy values correctly via `_peek()`.
- `utils/log_filter.py` — `RateLimitFilter(max_identical=2, quiet=300)` attached to the cog handler.
- Hot-path cogs now read config via `ConfigCache` + `fetch_safe(single=True)`; config is cached ~15–20s, invalidated on writes; DB-down = "unconfigured" no-op instead of a crash/log flood per event:
  - `cogs/confessions.py` (guarded `on_message`), `cogs/counting.py` (config + progress caches), `cogs/avatar_check.py` (guarded `on_user_update`), `cogs/greetings.py` (dict cache → `ConfigCache[GuildConfig]`, guarded listeners), `cogs/invite_tracker.py` (cached trait/paperwork lookups, guarded `on_member_remove`/`on_invite_create`), `cogs/tempvoice.py` (cached `guild_config`, guarded `on_voice_state_update`).
- `cogs/mines.py` — `_payout_lock` serializes payout; `game.finished = True` set inside the lock before `update_balance`; bomb/jackpot/safe/cashout side effects isolated in `run_side_effects(hunger_inc, mood_inc)`; `on_timeout` marks finished before refund and is fully try/except guarded.
- `cogs/quests.py` — `trigger_event` swallows infra errors (42501/PGRST205 → debug), other exceptions logged with `exc_info`; never crashes callers.
- `cogs/economy.py` — real `logger` (no `__import__("logging")`); per-user `asyncio.Lock` around `update_balance`, separate work lock around `/work` cooldown + write; `work_phrases` via `fetch_safe`.
- `cogs/moderation.py` — `on_voice_state_update` guarded (uses `fetch_safe`, infra errors → debug); background loops already crash-safe per-guild.
- `main.py` — `logger.exception(...)` → `logger.error(..., exc_info=exc)` in command/slash handlers; `RateLimitFilter` on cog handler; startup DB `health_check` after `init_tables` prints a single actionable line (schema incomplete / privileges incomplete / ✅).
- `tools/check_migration_applied.py` — reports each table as `OK | MISSING | PERMISSION | UNAVAILABLE | ERROR` with classified causes and a summary + remediation pointers.

## 3. Tests

- `tests/test_config_cache.py` — TTL caching, falsy values, invalidation, coalescing.
- `tests/test_supabase_manager_classify.py` — error classification (codes + strings), `fetch_safe` dedup logging behavior.
- `tests/test_mines_logic.py` — reveal lifecycle, jackpot, double-cashout pays once, cashout-then-timeout no double refund, bomb-vs-cashout mutual exclusion.

Result: **65 passed**, `py_compile` clean on all changed/new files, all 17 touched modules import.

## 4. Deployment steps

1. Apply the migration in the Supabase SQL Editor (idempotent — safe to paste fully):
   ```
   database/migrations/20260914_repair_runtime_schema.sql
   ```
   (If you prefer a clean slate, run `database/migrations/000_complete_schema.sql` first — it already creates everything and grants `service_role`.)
2. Verify with:
   ```
   python tools/check_migration_applied.py
   ```
   Expect `OK` for all listed tables (summary should show `OK=N, MISSING=0, PERMISSION=0`).
3. Restart the bot. On startup `main.py` logs the health check result.

## 5. Before / after

| Metric | Before | After |
|---|---|---|
| Per-message config reads (confession/counting) | DB fetch every message | cached, refreshed ≤ ~20s |
| Per-table failure logging | full traceback per event | 1 full log + silent count + compact summary per 10 min |
| Race/crash risk in mines cashout | double-pay possible | locked, `finished` set under lock |
| `update_balance` concurrent writes | lost updates | per-user lock |
| Global error handler output | masked by `NoneType: None` bug | real error + traceback |
| Startup DB state | unknown, silent | explicit health check report |
| `on_voice_state_update` | raised on missing table | guarded no-op until DB fixed |
| Tests | none | 65 passing |