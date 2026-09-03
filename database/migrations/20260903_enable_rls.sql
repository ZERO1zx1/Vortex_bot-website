-- ============================================================================
-- 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 - Enable RLS on all public tables + fix increment() search_path
-- Date: 2026-09-03
--
-- Resolves the Supabase database-linter findings:
--   0007_policy_exists_rls_disabled  - bot_status has policies but RLS off
--   0013_rls_disabled_in_public      - public tables with RLS disabled
--   0011_function_search_path_mutable - increment() has a mutable search_path
--
-- Security model:
--   The bot and the static status page both operate with the anon (public)
--   key. To keep them working while enabling RLS, every public table gets an
--   explicit "allow all" policy (USING(true) / WITH CHECK(true)) — matching
--   the existing conventions on `user_equips` and `bot_status`. RLS is now
--   ON so the access contract is declarative and can be tightened later
--   without breaking current behaviour.
--
-- The ENABLE + policy creation is wrapped in a DO block so it is idempotent
-- and named policies are (re)created unconditionally.
-- ============================================================================

DO $$
DECLARE
    t TEXT;
BEGIN
    FOR t IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename NOT LIKE 'pg_%'
          AND tablename <> 'supabase_migrations'
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'allow_all_' || t, t);
        EXECUTE format(
            'CREATE POLICY %I ON %I FOR ALL USING (true) WITH CHECK (true)',
            'allow_all_' || t, t
        );
    END LOOP;
END;
$$;

-- ============================================================================
-- Fix increment(): pin an immutable, safe search_path so the function cannot
-- be hijacked by a malicious schema earlier in the caller's search_path.
-- ============================================================================
ALTER FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    SET search_path = pg_catalog, public;

-- Tell PostgREST to refresh its schema cache
NOTIFY pgrst, 'reload schema';
