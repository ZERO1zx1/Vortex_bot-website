-- ============================================================
-- Migration: 20260918_003_repair_permissions.sql
-- Bot: Vortex/Aether — Production 42501 / PGRST205 иж бүрэн засвар
-- Idempotent: олон удаа ажиллуулж болно.
-- ============================================================

-- ── (0) Шинэ-д үүссэн table-ууд service_role GRANT-той байх нөхцөл ──
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO service_role;

-- ── (1) Бүх public table дээр service_role-д иж бүрэн GRANT ──
DO $$
DECLARE t TEXT;
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename NOT LIKE 'pg_%'
      AND tablename <> 'supabase_migrations'
  LOOP
    EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE %I TO service_role', t);
  END LOOP;
END;
$$;

-- ── (2) Sequences: SERIAL id колонкууд ажиллах нөхцөл ──
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;

-- ── (3) Functions: increment RPC гэх мэт ──
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- ── (4) RLS: идэвхжүүл (service_role bypass хийдэг тул айхгүй) ──
DO $$
DECLARE t TEXT;
BEGIN
  FOR t IN
    SELECT tablename FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename <> 'supabase_migrations'
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('REVOKE ALL PRIVILEGES ON TABLE %I FROM anon, authenticated', t);
  END LOOP;
END;
$$;

-- ── (5) Website heartbeat: зөвхөн bot_status id=1 SELECT нь public ──
GRANT SELECT ON TABLE public.bot_status TO anon;
DROP POLICY IF EXISTS anon_read_bot_status ON public.bot_status;
CREATE POLICY anon_read_bot_status ON public.bot_status
  FOR SELECT TO anon USING (id = 1);

-- ── (6) PostgREST schema cache шинэчлэх ──
NOTIFY pgrst, 'reload schema';