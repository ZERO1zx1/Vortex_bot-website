# Supabase Database Design

## Intent

Replace Aether's local SQLite runtime database with a new, empty Supabase
PostgreSQL database so the Discord bot has durable hosted storage.

## Goals

- Connect the long-running bot through `DATABASE_URL` using `asyncpg`.
- Use Supabase's Session pooler on port 5432 with TLS.
- Preserve the repository and service APIs, including atomic money operations.
- Provide PostgreSQL migrations that create the complete schema and seed catalog.
- Keep credentials only in environment configuration.
- Keep the test suite runnable without a real Supabase password.

## Non-goals

- Migrate data from the current SQLite file.
- Add Supabase Auth, Storage, Realtime, or frontend Data API access.
- Provision a Supabase project or commit a live database password.
- Support SQLite in production.

## Constraints

- Python 3.13 and `discord.py` remain unchanged.
- Public repository and service contracts stay stable where practical.
- Monetary changes must remain atomic and append-only audit tables immutable.
- The bot must fail clearly when `DATABASE_URL` is absent or malformed.
- SQL must use PostgreSQL syntax and positional parameters accepted by `asyncpg`.

## Approaches

1. **Direct PostgreSQL with `asyncpg` (selected).** Keeps raw SQL repositories and
   real transactions while replacing the database boundary and SQL dialect.
2. **Supabase Python REST client.** Rejected because multi-step economy operations
   would require repository rewrites and database RPC functions for atomicity.
3. **Dual SQLite/PostgreSQL runtime.** Rejected because maintaining two dialects
   adds complexity and leaves production behavior under-tested.

## Design

`config.py` reads a required `DATABASE_URL`. `Database` owns one `asyncpg` pool,
acquires one connection for each transaction, and uses a task-local transaction
state for nested service calls. Queries outside explicit transactions borrow a
connection from the pool. Repository rows remain mapping-like records, so their
dataclass conversion stays stable.

PostgreSQL migrations live separately from the deleted SQLite migration history.
They use `BIGINT` Discord IDs, identity columns, `TIMESTAMPTZ`, `JSONB`, foreign
keys, checks, indexes, seed upserts, and trigger functions that reject updates or
deletes on audit ledgers. A checksum table prevents an applied migration from
being silently changed.

Tests use an isolated in-process database test double for service behavior and
mocked `asyncpg` pools for connection/transaction contracts. An opt-in integration
test validates the schema against a disposable PostgreSQL/Supabase database when
`AETHER_TEST_DATABASE_URL` is supplied.

## Deployment boundary

The code and schema can be prepared and verified locally without secrets. Applying
the schema to the user's Supabase project requires a locally configured
`DATABASE_URL` or `AETHER_TEST_DATABASE_URL`; the URL is never printed or committed.
