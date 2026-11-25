# Supabase Database Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Replace Aether's SQLite runtime with a new Supabase PostgreSQL database while preserving atomic repository and service behavior.

**Architecture:** `asyncpg` provides a small application-side pool over Supabase's TLS Session pooler. The existing repository boundary remains raw SQL, while `Database` translates its transaction/query contract to PostgreSQL and migrations create a fresh schema.

**Tech Stack:** Python 3.13, asyncpg, PostgreSQL/Supabase, pytest, discord.py

**Spec:** `docs/superpowers/specs/2026-11-24-supabase-database-design.md`

## Global Constraints

- Production supports PostgreSQL/Supabase only; no SQLite runtime fallback.
- Never commit or print `DATABASE_URL` or a database password.
- Keep repository and service public APIs stable where practical.
- Preserve atomic money operations and immutable audit ledgers.
- Tests must run without access to the user's live Supabase project.

## Review Focus

- Missing or malformed `DATABASE_URL` must stop startup with a clear configuration error.
- Session-pooler connections must require TLS and must not depend on unsupported session state.
- Nested service calls must share the outer connection and roll back as one transaction.
- Concurrent tasks must never inherit or reuse another task's active transaction.
- Reapplying migrations must be idempotent, while changed applied migrations must fail checksum validation.

---

### Task 1: Configuration and PostgreSQL dependency

**Files:**
- Modify: `aether_bot/config.py`
- Modify: `aether_bot/.env.example`
- Modify: `aether_bot/requirements.txt`
- Modify: `aether_bot/requirements-dev.txt`
- Test: `aether_bot/tests/test_config.py`

**Interfaces:**
- Produces: `Settings.database_url: str` and `config.DATABASE_URL: str`
- Consumes: environment variable `DATABASE_URL`

- [x] Add failing tests for missing, whitespace-only, and valid PostgreSQL URLs.
- [x] Run `pytest tests/test_config.py -q` and confirm the new tests fail.
- [x] Replace `AETHER_DB_PATH` parsing with required `DATABASE_URL` validation and replace `aiosqlite` with a pinned `asyncpg` dependency.
- [x] Run `pytest tests/test_config.py -q` and confirm it passes.

### Task 2: Async PostgreSQL database boundary

**Files:**
- Replace: `aether_bot/core/database.py`
- Test: `aether_bot/tests/test_database.py`

**Interfaces:**
- Consumes: `Database(database_url: str, migrations_dir: str | Path | None)`
- Produces: `connect`, `close`, `transaction`, `execute`, `insert`, `executemany`, `fetchone`, `fetchall`, `fetchval`, `fetchval_write`, `connected`, and `in_transaction`

- [x] Write mocked-pool tests for TLS pool creation, lifecycle, row mapping, automatic transactions, explicit rollback, nested transactions, cross-task rejection, and migration checksum behavior.
- [x] Run focused database tests and confirm they fail against the SQLite implementation.
- [x] Implement the minimal `asyncpg` pool and task-local transaction boundary; normalize `?` placeholders only after repositories have moved to native `$n` parameters.
- [x] Implement a PostgreSQL migration runner that applies each file in one transaction and records SHA-256 checksums.
- [x] Run the database tests and confirm they pass.

### Task 3: PostgreSQL schema and repository SQL

**Files:**
- Replace: `aether_bot/migrations/*.sql`
- Modify: `aether_bot/repositories/*.py`
- Modify: `aether_bot/utils/time_utils.py`
- Test: `aether_bot/tests/test_repositories.py`
- Test: `aether_bot/tests/test_repositories_extra.py`

**Interfaces:**
- Consumes: the Task 2 `Database` query API with asyncpg `$1..$n` parameters
- Produces: the existing repository dataclasses and methods over PostgreSQL rows

- [x] Add tests pinning PostgreSQL parameter syntax, upserts, `RETURNING`, JSONB serialization, timestamp handling, ledger immutability, and all expected schema objects.
- [x] Run repository tests and confirm dialect failures.
- [x] Create a fresh PostgreSQL baseline migration with full schema, seed data, constraints, indexes, and append-only trigger functions.
- [x] Convert every repository query from SQLite syntax to PostgreSQL syntax and return inserted identity IDs explicitly.
- [x] Update timestamp helpers to accept PostgreSQL timezone-aware datetimes while preserving string compatibility at service boundaries.
- [x] Run repository tests and confirm they pass.

### Task 4: Bot wiring and offline service-test database

**Files:**
- Modify: `aether_bot/bot.py`
- Modify: `aether_bot/tests/conftest.py`
- Create: `aether_bot/tests/fakes/database.py`
- Modify: service tests that make SQLite-specific assertions
- Test: `aether_bot/tests/test_bot.py`

**Interfaces:**
- Consumes: `config.DATABASE_URL` and Task 2 `Database`
- Produces: production bot startup over Supabase and deterministic offline tests

- [x] Add a bot construction test asserting it passes `DATABASE_URL` to `Database` without connecting during import.
- [x] Add contract tests ensuring the offline test double matches the database methods used by repositories and services.
- [x] Run bot and representative service tests and confirm they fail before rewiring.
- [x] Wire the bot to PostgreSQL and move SQLite-only test support into the tests package so production cannot select it.
- [x] Remove SQLite-specific test cases and replace them with database-contract or opt-in PostgreSQL integration assertions.
- [x] Run all service and bot tests and confirm they pass.

### Task 5: Documentation and end-to-end verification

**Files:**
- Modify: `aether_bot/README.md`
- Modify: `aether_bot/docs/ARCHITECTURE.md`
- Modify: `Dockerfile`
- Modify: `.github/workflows/test.yml`
- Test: `aether_bot/tests/test_imports.py`

**Interfaces:**
- Consumes: Tasks 1-4
- Produces: setup instructions for Supabase Session pooler and optional live schema validation

- [x] Update documentation with the Connect → Session pooler → `.env` flow, TLS behavior, migration startup, and secret-handling rules.
- [x] Add an opt-in integration check guarded by `AETHER_TEST_DATABASE_URL`; it creates the fresh schema and verifies seed counts without touching a production URL.
- [x] Run formatting, lint, type checking, compile checks, and the full offline test suite.
- [ ] If a disposable test URL is available, run the opt-in PostgreSQL integration test and report the database target only as redacted host metadata.
- [x] Review `git diff` to ensure SQLite is absent from production dependencies, code, migrations, and documentation.
