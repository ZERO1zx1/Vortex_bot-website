-- Directed family links used by the interactive /marriage guide.
-- Every accepted request is stored in both directions for fast profile reads.
CREATE TABLE IF NOT EXISTS public.family_relationships (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    relative_id TEXT NOT NULL,
    relation_type TEXT NOT NULL CHECK (relation_type IN (
        'grandfather', 'grandmother', 'grandchild',
        'father', 'mother', 'child', 'parent',
        'older_brother', 'older_sister', 'younger_sibling',
        'younger_brother', 'younger_sister', 'older_sibling'
    )),
    created_at BIGINT NOT NULL DEFAULT (EXTRACT(EPOCH FROM NOW())::BIGINT),
    PRIMARY KEY (guild_id, user_id, relative_id),
    CHECK (user_id <> relative_id)
);

CREATE INDEX IF NOT EXISTS idx_family_relationships_relative
    ON public.family_relationships (guild_id, relative_id);

ALTER TABLE public.family_relationships ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_role_family_relationships" ON public.family_relationships;
CREATE POLICY "service_role_family_relationships"
    ON public.family_relationships
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

NOTIFY pgrst, 'reload schema';
