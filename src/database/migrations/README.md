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

If 005 was applied before the 2026-10-04 repair, re-run the corrected 005
before using PvP or reward retries. The repair rejects overdrafts, preserves
the balance cap, uses BIGINT values in the replay result, and explicitly adds
the tax column to reference tables created by migration 003. Existing reference
rows are retained with tax defaulting to zero. Updating the
local SQL file alone does not update the deployed function.

For an existing project, run `006_treasury_atomic.sql` before enabling
Government treasury payments. It installs the `treasury_payments` idempotency
table and the atomic `treasury_pay_once` RPC. Apply it after the bootstrap and
earlier incremental migrations.

For an existing project, run `008_economy_command_cooldowns.sql` before
deploying the current Economy and Casino cogs. It adds the persistent
`last_crime` / `last_rob` / `last_hack` / `last_give` columns to `economy` so
the money-faucet and rate-limit cooldowns survive a bot restart instead of
living only in process memory. Apply it after the bootstrap and earlier
incremental migrations.

For an existing project, run `009_economy_transfer_atomic.sql` before relying
on the atomic transfer path. It installs the `economy_transfer_references`
table and the `apply_economy_transfer_once` RPC, which debits the sender,
credits the receiver and distributes the transfer tax in one transaction.
Until it is applied the bot falls back to the locked two-write path, which is
safe within a single process but can lose the amount if the process dies
between the two writes.

For an existing project, run `010_counting_progression.sql` before deploying
the Counting progression update. It adds separate spendable/lifetime Counting
XP, level and save-token state, weekly-shield timestamps, the persisted
anti-farm participant window, and optional Level 5/20/50 role IDs.

`reference` makes reward and treasury mutations exactly-once. The 005 RPC
commits the recipient balance and tax distribution in one transaction; replay
of the same reference returns the committed result without applying tax again.

`economy_balance_references` is append-only for audit and deduplication. The
`created_at` index supports a future retention job; do not delete references
inside the maximum retry/replay window.

The dated SQL files are incremental migrations. Apply only the migrations that
the target project has not applied; do not blindly replay them on a live
project without checking the schema and migration history.
