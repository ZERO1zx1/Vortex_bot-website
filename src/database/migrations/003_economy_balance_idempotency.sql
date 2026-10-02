CREATE TABLE IF NOT EXISTS economy_balance_references (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    delta BIGINT NOT NULL,
    balance_after BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_economy_balance_references_created_at
    ON economy_balance_references (created_at);

ALTER TABLE economy_balance_references ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE economy_balance_references TO service_role;

CREATE OR REPLACE FUNCTION apply_economy_balance_once(
    p_reference TEXT,
    p_user_id TEXT,
    p_guild_id TEXT,
    p_delta BIGINT,
    p_max_balance BIGINT
) RETURNS TABLE(applied BOOLEAN, balance BIGINT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing economy_balance_references%ROWTYPE;
    v_balance BIGINT;
BEGIN
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_max_balance < 0 THEN
        RAISE EXCEPTION 'max balance must be non-negative';
    END IF;

    INSERT INTO economy_balance_references (reference, user_id, guild_id, delta)
    VALUES (p_reference, p_user_id, p_guild_id, p_delta)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        SELECT * INTO v_existing
        FROM economy_balance_references
        WHERE reference = p_reference;

        IF v_existing.user_id IS DISTINCT FROM p_user_id
           OR v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.delta IS DISTINCT FROM p_delta THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.balance_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed balance result', p_reference;
        END IF;

        RETURN QUERY SELECT FALSE, v_existing.balance_after;
        RETURN;
    END IF;

    UPDATE economy
    SET balance = LEAST(
        p_max_balance,
        COALESCE(economy.balance, 0) + p_delta
    )
    WHERE user_id = p_user_id
      AND guild_id = p_guild_id
      AND COALESCE(economy.balance, 0) + p_delta >= 0
    RETURNING economy.balance INTO v_balance;

    IF v_balance IS NULL THEN
        IF EXISTS (
            SELECT 1 FROM economy
            WHERE user_id = p_user_id AND guild_id = p_guild_id
        ) THEN
            RAISE EXCEPTION 'insufficient balance for user % in guild %', p_user_id, p_guild_id;
        END IF;
        RAISE EXCEPTION 'economy account not found for user % in guild %', p_user_id, p_guild_id;
    END IF;

    UPDATE economy_balance_references
    SET balance_after = v_balance
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_balance;
END;
$$;

REVOKE ALL ON FUNCTION apply_economy_balance_once(TEXT, TEXT, TEXT, BIGINT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION apply_economy_balance_once(TEXT, TEXT, TEXT, BIGINT, BIGINT) TO service_role;

NOTIFY pgrst, 'reload schema';
