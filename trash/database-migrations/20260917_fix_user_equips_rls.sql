-- ============================================================================
-- AETHER: tighten user_equips RLS (linter finding rls_policy_always_true)
-- Date: 2026-09-17
--
-- The equip system (cogs/shop.py) runs server-side with
-- SUPABASE_SERVICE_ROLE_KEY, which bypasses RLS. No anonymous / authenticated
-- client path reads or writes user_equips, so the blanket
-- FOR ALL USING (true) WITH CHECK (true) policy only broadened access.
--
-- Remediation: drop the permissive policy, keep RLS enabled with no policies,
-- and grant service_role explicitly (it bypasses RLS regardless). The linter
-- explicitly allows SELECT USING (true) for public reads, but none is needed
-- here because the bot is the only caller.
-- ============================================================================

DROP POLICY IF EXISTS "bot full access user_equips" ON public.user_equips;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.user_equips TO service_role;

ALTER TABLE public.user_equips ENABLE ROW LEVEL SECURITY;

NOTIFY pgrst, 'reload schema';