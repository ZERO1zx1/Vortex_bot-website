# Aether cog audit report

Date: 2026-11-08  
Scope: `src/cogs/**`, offline diagnostics, command catalog, website build

## Result

The offline audit completed successfully after repairing four diagnostics that
still referenced the old project layout or an incomplete fake context. The
runtime code was not changed by this pass; the changes make the verification
tools reflect the current package structure and exercise the intended inputs.

Coverage: 28/28 active cogs loaded, 110 runtime commands registered, 344
pytest tests passed and 1 skipped, 219 help embeds passed Discord size checks,
179 website catalog entries validated with no drift, and the website production
build completed successfully.

## Cog coverage

- `admin`: administration, automod, level administration, moderation, webhooks
- `community`: confessions, giveaways, greetings, marriage/family, tickets
- `economy`: economy, government, leaderboard
- `games`: anime clash, casino, counting, fun, games, leveling, PvP, Texas poker
- `shop`: cafe, carts, shop, trade
- `system`: help, menu, presence

## Findings

### [1] Diagnostics used a removed games module path
- Location          : `tools/smoke_test.py:88`
- Severity          : MEDIUM
- Class             : TEST FAILURE
- Root Cause proven : The project moved the games cog to `src/cogs/games/games.py`, while the smoke probe still loaded `src/cogs/games.py`.
- Confidence        : 1.0
- Impact            : The game UI smoke test could not start; runtime bot code was unaffected.
- Reproduce         : `./.venv/bin/python tools/smoke_test.py`
- Fix               : Updated the probe path and loaded the actual exceptions module.
- Re-validate       : `./.venv/bin/python tools/smoke_test.py`
- Expected / Actual : All views and commands load / all passed
- Status            : FIXED
- Proposed by       : ai-agent
- Confirmed by      : PENDING
- Evidence          : Exit code 0; game views and command checks passed.

### [2] Command smoke used a member without guild context
- Location          : `tools/test_all_commands.py:236`
- Severity          : MEDIUM
- Class             : TEST FAILURE
- Root Cause proven : The fake required Member parameter was created before the fake Context and retained `guild=None`; level-up announcement correctly dereferenced `member.guild`.
- Confidence        : 1.0
- Impact            : The `addxp` command smoke path failed before reaching its intended behavior.
- Reproduce         : `./.venv/bin/python tools/test_all_commands.py`
- Fix               : Attach the simulated context guild to fake Member parameters before invoking callbacks.
- Re-validate       : `./.venv/bin/python tools/test_all_commands.py`
- Expected / Actual : 5/5 command paths pass / 5/5 pass
- Status            : FIXED
- Proposed by       : ai-agent
- Confirmed by      : PENDING
- Evidence          : `adminpanel`, `workphrase`, `addxp`, `removexp`, `leveling_setup` all OK.

### [3] Staff and help probes drifted from current ownership
- Location          : `tools/smoke_staff.py:18`, `tools/test_help_embeds.py:25`
- Severity          : MEDIUM
- Class             : TEST FAILURE
- Root Cause proven : Staff probe mocked `src.core.config` without the public functions imported by `src.core`; help probe loaded removed `src/cogs/help.py` instead of `src/cogs/system/help.py`.
- Confidence        : 1.0
- Impact            : Two important offline validation tools failed independently of bot behavior.
- Reproduce         : `./.venv/bin/python tools/smoke_staff.py && ./.venv/bin/python tools/test_help_embeds.py`
- Fix               : Removed the incomplete config mock and updated the help cog path; preserved the intentional admin utility commands in the assertion.
- Re-validate       : Same command
- Expected / Actual : Staff, help, trade probes pass / all pass
- Status            : FIXED
- Proposed by       : ai-agent
- Confirmed by      : PENDING
- Evidence          : Staff checks passed; category embeds 18/18 and detail embeds 219/219 passed; trade UI passed.

### [4] Production boundary remains external
- Location          : `.env:?`, `src/core/config.py:?`
- Severity          : HIGH
- Class             : ENV FAILURE
- Root Cause proven : Offline validation cannot prove that the configured Supabase server-level key is valid or that the bot can connect to Discord production gateway.
- Confidence        : 1.0
- Impact            : Deployment/runtime availability depends on external credentials and provider state.
- Reproduce         : `./.venv/bin/python -m src.main`
- Fix               : Verify `SUPABASE_SECRET_KEY` or a valid server-role key and production Discord credentials outside this offline audit.
- Re-validate       : Run the bot in the configured deployment environment and inspect startup/database health logs.
- Expected / Actual : Live provider health / not verifiable offline
- Status            : STATIC-RISK
- Proposed by       : ai-agent
- Confirmed by      : PENDING
- Evidence          : Startup diagnostics reported Supabase key naming/value mismatch; no live provider call was made.
- Boundary Note     : No secrets are included in this report.

## Commands run

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall -q src tools main.py
./.venv/bin/python tools/probe_load_all_cogs.py
./.venv/bin/python tools/smoke_test.py
./.venv/bin/python tools/test_all_commands.py
./.venv/bin/python tools/smoke_staff.py
./.venv/bin/python tools/test_help_embeds.py
./.venv/bin/python tools/smoke_trade_ui.py
./.venv/bin/python tools/probe_load_shop_trade.py
(cd website && npm run validate:commands && npm run build)
```

## Changed files

`tools/smoke_test.py`, `tools/test_all_commands.py`, `tools/smoke_staff.py`,
`tools/test_help_embeds.py`, `website/src/App.jsx`,
`website/src/components/AuditReport.jsx`, `website/src/i18n/dictionary.js`,
and `website/src/styles/style.css`.

## Remaining boundaries

The audit did not deploy the bot, connect to Discord, or mutate Supabase data.
The local AgentCore audit command is unavailable because this repository does
not contain the expected `src.cli` installation. `ruff` is also not installed
in the local environment.
