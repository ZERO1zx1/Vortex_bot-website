-- Atomic two-party economy transfer.
--
-- The transfer command moved money with two separate balance writes. A crash
-- between them destroyed the amount: the sender was debited and the receiver
-- was never credited.  This RPC debits the sender, credits the receiver and
-- distributes the transfer tax in one transaction, and claims a reference so
-- a retry replays the committed result instead of transferring twice.
--
-- Both economy rows are locked in a deterministic order, so a concurrent
-- A->B / B->A pair cannot deadlock.

CREATE TABLE IF NOT EXISTS economy_transfer_references (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    from_user_id TEXT NOT NULL,
    from_guild_id TEXT NOT NULL,
    to_user_id TEXT NOT NULL,
    to_guild_id TEXT NOT NULL,
    amount BIGINT NOT NULL,
    tax BIGINT NOT NULL DEFAULT 0,
    from_balance_after BIGINT,
    to_balance_after BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_economy_transfer_references_created_at
    ON economy_transfer_references (created_at);

ALTER TABLE economy_transfer_references ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE economy_transfer_references TO service_role;

CREATE OR REPLACE FUNCTION apply_economy_transfer_once(
    p_reference TEXT,
    p_from_user_id TEXT,
    p_from_guild_id TEXT,
    p_to_user_id TEXT,
    p_to_guild_id TEXT,
    p_amount BIGINT,
    p_max_balance BIGINT,
    p_tax BIGINT,
    p_credits JSONB,
    p_treasury BIGINT,
    p_discarded BIGINT
) RETURNS TABLE(
    applied BOOLEAN,
    from_balance BIGINT,
    to_balance BIGINT,
    tax_shipped BIGINT
) LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing economy_transfer_references%ROWTYPE;
    v_from_balance BIGINT;
    v_to_balance BIGINT;
    v_credit_record RECORD;
    v_tax_shipped BIGINT := 0;
BEGIN
    -- Validate inputs
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_amount IS NULL OR p_amount <= 0 THEN
        RAISE EXCEPTION 'transfer amount must be positive';
    END IF;
    IF p_max_balance < 0 THEN
        RAISE EXCEPTION 'max balance must be non-negative';
    END IF;
    IF p_tax < 0 OR p_tax > p_amount THEN
        RAISE EXCEPTION 'tax must be between zero and the transfer amount';
    END IF;
    IF p_treasury < 0 THEN
        RAISE EXCEPTION 'treasury must be non-negative';
    END IF;
    IF p_discarded < 0 THEN
        RAISE EXCEPTION 'discarded must be non-negative';
    END IF;
    IF p_from_user_id = p_to_user_id AND p_from_guild_id = p_to_guild_id THEN
        RAISE EXCEPTION 'cannot transfer to the same account';
    END IF;

    -- Verify credits JSONB is an array of objects with user_id, amount
    IF p_credits IS NOT NULL AND jsonb_typeof(p_credits) <> 'array' THEN
        RAISE EXCEPTION 'credits must be a JSON array';
    END IF;
    IF p_credits IS NOT NULL AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_credits) AS elem
        WHERE jsonb_typeof(elem) <> 'object'
           OR COALESCE(elem->>'user_id', '') !~ '^[0-9]+$'
           OR COALESCE(elem->>'amount', '') !~ '^[0-9]+$'
    ) THEN
        RAISE EXCEPTION 'credits entries must contain numeric user_id and amount';
    END IF;
    IF p_credits IS NOT NULL AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(p_credits) AS elem
        GROUP BY elem->>'user_id'
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'credits user_id values must be unique';
    END IF;
    IF COALESCE((
        SELECT SUM((elem->>'amount')::BIGINT)
        FROM jsonb_array_elements(COALESCE(p_credits, '[]'::JSONB)) AS elem
    ), 0) + p_treasury + p_discarded <> p_tax THEN
        RAISE EXCEPTION 'tax distribution must equal tax amount';
    END IF;

    -- Claim the reference (idempotency key)
    INSERT INTO economy_transfer_references (
        reference, from_user_id, from_guild_id, to_user_id, to_guild_id, amount, tax
    )
    VALUES (
        p_reference, p_from_user_id, p_from_guild_id, p_to_user_id, p_to_guild_id, p_amount, p_tax
    )
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        SELECT * INTO v_existing
        FROM economy_transfer_references
        WHERE reference = p_reference;

        IF v_existing.from_user_id IS DISTINCT FROM p_from_user_id
           OR v_existing.from_guild_id IS DISTINCT FROM p_from_guild_id
           OR v_existing.to_user_id IS DISTINCT FROM p_to_user_id
           OR v_existing.to_guild_id IS DISTINCT FROM p_to_guild_id
           OR v_existing.amount IS DISTINCT FROM p_amount
           OR v_existing.tax IS DISTINCT FROM p_tax THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.from_balance_after IS NULL OR v_existing.to_balance_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed transfer result', p_reference;
        END IF;

        -- Return the originally committed result (no re-distribution)
        RETURN QUERY SELECT FALSE, v_existing.from_balance_after, v_existing.to_balance_after, 0::BIGINT;
        RETURN;
    END IF;

    -- Lock both rows in a deterministic order so two opposing transfers
    -- cannot deadlock: one waits for the other instead of locking in
    -- opposite order.
    PERFORM 1
    FROM economy
    WHERE (user_id, guild_id) IN (
        (p_from_user_id, p_from_guild_id),
        (p_to_user_id, p_to_guild_id)
    )
    ORDER BY user_id, guild_id
    FOR UPDATE;

    -- 1. Debit the sender. The balance guard rejects an overdraft.
    UPDATE economy
    SET balance = COALESCE(balance, 0) - p_amount
    WHERE user_id = p_from_user_id
      AND guild_id = p_from_guild_id
      AND COALESCE(balance, 0) >= p_amount
    RETURNING economy.balance INTO v_from_balance;

    IF v_from_balance IS NULL THEN
        IF EXISTS (
            SELECT 1 FROM economy
            WHERE user_id = p_from_user_id AND guild_id = p_from_guild_id
        ) THEN
            RAISE EXCEPTION 'insufficient balance for user % in guild %', p_from_user_id, p_from_guild_id;
        END IF;
        RAISE EXCEPTION 'economy account not found for user % in guild %', p_from_user_id, p_from_guild_id;
    END IF;

    -- 2. Credit the receiver with the untaxed remainder.
    UPDATE economy
    SET balance = LEAST(p_max_balance, COALESCE(balance, 0) + (p_amount - p_tax))
    WHERE user_id = p_to_user_id
      AND guild_id = p_to_guild_id
    RETURNING economy.balance INTO v_to_balance;

    IF v_to_balance IS NULL THEN
        RAISE EXCEPTION 'economy account not found for user % in guild %', p_to_user_id, p_to_guild_id;
    END IF;

    -- 3. Credit tax recipients
    IF p_credits IS NOT NULL AND jsonb_array_length(p_credits) > 0 THEN
        FOR v_credit_record IN
            SELECT (elem->>'user_id')::TEXT AS uid, (elem->>'amount')::BIGINT AS amt
            FROM jsonb_array_elements(p_credits) AS elem
        LOOP
            IF v_credit_record.amt > 0 THEN
                INSERT INTO economy (user_id, guild_id, balance)
                VALUES (v_credit_record.uid, p_from_guild_id, v_credit_record.amt)
                ON CONFLICT (user_id, guild_id) DO UPDATE
                    SET balance = LEAST(p_max_balance, economy.balance + v_credit_record.amt);
                v_tax_shipped := v_tax_shipped + v_credit_record.amt;
            END IF;
        END LOOP;
    END IF;

    -- 4. Increment treasury
    IF p_treasury > 0 THEN
        UPDATE economy_guild_settings
        SET treasury_balance = treasury_balance + p_treasury,
            updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
        WHERE guild_id = p_from_guild_id;
    END IF;

    -- 5. Ledger entries are written by the caller (Economy.record_money) so
    -- the fallback path produces the same audit trail as the RPC path.

    -- 6. Record the completed balances in the reference table
    UPDATE economy_transfer_references
    SET from_balance_after = v_from_balance,
        to_balance_after = v_to_balance
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_from_balance, v_to_balance, v_tax_shipped;
END;
$$;

REVOKE ALL ON FUNCTION apply_economy_transfer_once(TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION apply_economy_transfer_once(TEXT, TEXT, TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) TO service_role;

NOTIFY pgrst, 'reload schema';
