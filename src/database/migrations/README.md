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

`reference` makes the recipient balance mutation exactly-once. Tax routing is
currently a post-commit, best-effort side effect because it can depend on live
Discord roles and Government recipients. If tax distribution raises after the
balance RPC commits, retrying the same reference will not credit the player
again and will not automatically replay that tax. Treat this as a known safety
tradeoff until tax delivery gets its own durable outbox/idempotency contract.

`economy_balance_references` is append-only for audit and deduplication. The
`created_at` index supports a future retention job; do not delete references
inside the maximum retry/replay window.

The other dated SQL files were historical repair steps and are archived under
`trash/database-migrations/`. They have already been applied to the live
project and must not be replayed there.
