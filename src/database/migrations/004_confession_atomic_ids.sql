-- Allocate confession IDs atomically across bot processes and shards.
-- The row-level UPDATE lock serializes concurrent allocations per guild.
CREATE OR REPLACE FUNCTION allocate_confession_id(p_guild_id TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_allocated BIGINT;
BEGIN
    UPDATE confession_config
    SET next_id = next_id + 1
    WHERE guild_id = p_guild_id
    RETURNING next_id - 1 INTO v_allocated;

    IF v_allocated IS NULL THEN
        RAISE EXCEPTION 'confession config not found for guild %', p_guild_id;
    END IF;

    RETURN v_allocated;
END;
$$;

REVOKE ALL ON FUNCTION allocate_confession_id(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION allocate_confession_id(TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
