# Full repository audit — 2026-09-20

## Scope

Audited 166 tracked/source/config/test/deployment files, excluding binary GIF
payloads and installed font package contents. Reviewed bot cogs, shared utils,
database migrations, backend API, website assets/scripts, Docker/Railway/Firebase
configuration, tests, and current working-tree changes.

## Confirmed findings

### Fixed during this audit

- Runtime assets had moved from `assets/` to `assets/images/` while
  `fonts.py` and `leveling.py` still searched only the old paths. Font discovery
  now checks both locations and leveling uses the moved font path.
- `government.py` interaction responses no longer pass `view=None` to
  `discord.py` response methods.
- Shared `safe_respond()` now omits a missing view instead of sending
  `view=None`.

### Remaining risks

- Python/pytest cannot be executed in the current desktop environment because
  no Python interpreter is installed or discoverable. Runtime verification is
  still required in CI/Railway.
- Many cogs still construct embeds and respond directly instead of using the
  shared style/response helpers; full UI migration is incomplete.
- Economy/game payout flows still depend heavily on application-level locks;
  multi-process or multi-replica deployment needs database-side idempotency.
- Backend `/docs` and `/metrics` are public and have no rate limiting.
- Website JavaScript uses `innerHTML` for catalog/API-derived content; keep
  remote text escaped before expanding the API surface.
- Railway production is healthy, but source changes after the last deployment
  require a new deploy before runtime behavior changes.

## Validation limits

Static scans completed. Tests, imports, and live Discord interaction tests were
not run locally because Python is unavailable. No claim of full production
readiness is made until CI/Railway validation passes.
