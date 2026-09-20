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
--   * Discord bot and backend use SUPABASE_SERVICE_ROLE_KEY server-side.
--   * Browser clients never receive a Supabase key.
--   * anon may only SELECT the public bot_status heartbeat (legacy clients).
--   * authenticated has no direct access until a row-scoped policy exists.
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
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I', 'anon_read_' || t, t);
        EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
        EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
    END LOOP;
END;
$$;

GRANT SELECT ON TABLE public.bot_status TO anon;
CREATE POLICY anon_read_bot_status
    ON public.bot_status FOR SELECT TO anon USING (id = 1);

ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE USAGE, SELECT ON SEQUENCES FROM anon, authenticated;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
    REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated;

-- ============================================================================
-- Fix increment(): pin an immutable, safe search_path so the function cannot
-- be hijacked by a malicious schema earlier in the caller's search_path.
-- ============================================================================
ALTER FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    SET search_path = pg_catalog, public;
REVOKE ALL ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.increment(TEXT, TEXT, TEXT, TEXT, BIGINT)
    TO service_role;

-- Tell PostgREST to refresh its schema cache
NOTIFY pgrst, 'reload schema';
