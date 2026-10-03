# Aether database bootstrap

For a new Supabase project, run only `000_aether_complete.sql` once.

For an existing project that already ran the complete bootstrap before Anime
Clash profiles were added, run `001_anime_clash_profiles.sql` once.

For an existing project, run (or safely re-run) `002_poker_pending_payouts.sql`
before enabling Texas Poker. It installs the durable buy-in/refund marker and
atomic settlement RPCs used by the current cog.

For an existing project, run `003_economy_balance_idempotency.sql` once before
enabling retry-safe rewards that pass `reference` to `Economy.update_balance`.

For an existing project, run `004_confession_atomic_ids.sql` before deploying
the current Confessions cog. It moves confession-number allocation into one
atomic PostgreSQL `UPDATE ... RETURNING`, preventing duplicate IDs when
multiple bot processes or shards submit in the same guild.

For an existing project, run `005_economy_tax_atomic.sql` before deploying the
current Economy cog. It installs the atomic reward, tax, treasury, and discard
contract behind `apply_economy_balance_with_tax_once`.

For an existing project, run `006_treasury_atomic.sql` before enabling
Government treasury payments. It installs the `treasury_payments` idempotency
table and the atomic `treasury_pay_once` RPC. Apply it after the bootstrap and
earlier incremental migrations.

`reference` makes reward and treasury mutations exactly-once. The 005 RPC
commits the recipient balance and tax distribution in one transaction; replay
of the same reference returns the committed result without applying tax again.

`economy_balance_references` is append-only for audit and deduplication. The
`created_at` index supports a future retention job; do not delete references
inside the maximum retry/replay window.

The dated SQL files are incremental migrations. Apply only the migrations that
the target project has not applied; do not blindly replay them on a live
project without checking the schema and migration history.
