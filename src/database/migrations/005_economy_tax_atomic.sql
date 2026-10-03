-- ============================================================================
-- AETHER: Atomic reward + tax distribution (2026-10-02)
-- ----------------------------------------------------------------------------
-- Creates apply_economy_balance_with_tax_once RPC that atomically:
--   1. Claims a reference (idempotency key) in economy_balance_references
--   2. Updates the recipient's balance (capped at max_balance)
--   3. Credits tax recipients per the provided plan
--   4. Increments treasury_balance
--   5. Writes ledger entries for all mutations
-- All in a single PostgreSQL transaction.
--
-- Idempotency: same reference + identical payload → returns original result
--              same reference + different payload → raises exception
--              reference already applied → returns committed balance, no re-credit
--
-- This migration is idempotent and safe to run on existing projects.
-- ============================================================================

-- 1. Ensure the reference table exists (from 003_economy_balance_idempotency)
CREATE TABLE IF NOT EXISTS economy_balance_references (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    user_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    delta BIGINT NOT NULL,
    tax BIGINT NOT NULL DEFAULT 0,
    balance_after BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_economy_balance_references_created_at
    ON economy_balance_references (created_at);

ALTER TABLE economy_balance_references ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE economy_balance_references TO service_role;

-- 2. Atomic RPC: balance update + tax distribution in one transaction
CREATE OR REPLACE FUNCTION apply_economy_balance_with_tax_once(
    p_reference TEXT,
    p_user_id TEXT,
    p_guild_id TEXT,
    p_delta BIGINT,
    p_max_balance BIGINT,
    p_tax BIGINT,
    p_credits JSONB,
    p_treasury BIGINT,
    p_discarded BIGINT
) RETURNS TABLE(
    applied BOOLEAN,
    balance BIGINT,
    tax_shipped BIGINT,
    treasury BIGINT,
    discarded BIGINT
) LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing economy_balance_references%ROWTYPE;
    v_balance BIGINT;
    v_credit_record RECORD;
    v_tax_shipped BIGINT := 0;
BEGIN
    -- Validate inputs
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_max_balance < 0 THEN
        RAISE EXCEPTION 'max balance must be non-negative';
    END IF;
    IF p_tax < 0 THEN
        RAISE EXCEPTION 'tax must be non-negative';
    END IF;
    IF p_treasury < 0 THEN
        RAISE EXCEPTION 'treasury must be non-negative';
    END IF;
    IF p_discarded < 0 THEN
        RAISE EXCEPTION 'discarded must be non-negative';
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
    INSERT INTO economy_balance_references (reference, user_id, guild_id, delta, tax)
    VALUES (p_reference, p_user_id, p_guild_id, p_delta, p_tax)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        -- Reference already exists: verify payload matches, return committed result
        SELECT * INTO v_existing
        FROM economy_balance_references
        WHERE reference = p_reference;

        IF v_existing.user_id IS DISTINCT FROM p_user_id
           OR v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.delta IS DISTINCT FROM p_delta
           OR v_existing.tax IS DISTINCT FROM p_tax THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.balance_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed balance result', p_reference;
        END IF;

        -- Return the originally committed result (no re-distribution)
        RETURN QUERY SELECT FALSE, v_existing.balance_after, 0::BIGINT, 0::BIGINT, 0::BIGINT;
        RETURN;
    END IF;

    -- Initialize without crediting, then lock/update the account atomically.
    INSERT INTO economy (user_id, guild_id, balance)
    VALUES (p_user_id, p_guild_id, 0)
    ON CONFLICT (user_id, guild_id) DO NOTHING;
    UPDATE economy
    SET balance = LEAST(p_max_balance, COALESCE(economy.balance, 0) + p_delta)
    WHERE user_id = p_user_id
      AND guild_id = p_guild_id
      AND COALESCE(economy.balance, 0) + p_delta >= 0
    RETURNING economy.balance INTO v_balance;

    IF v_balance IS NULL THEN
        RAISE EXCEPTION 'insufficient balance for user % in guild %', p_user_id, p_guild_id;
    END IF;

    -- 2. Credit tax recipients (ON CONFLICT DO NOTHING for account init, then add amount)
    IF p_credits IS NOT NULL AND jsonb_array_length(p_credits) > 0 THEN
        FOR v_credit_record IN
            SELECT (elem->>'user_id')::TEXT AS uid, (elem->>'amount')::BIGINT AS amt
            FROM jsonb_array_elements(p_credits) AS elem
        LOOP
            IF v_credit_record.amt > 0 THEN
                INSERT INTO economy (user_id, guild_id, balance)
                VALUES (v_credit_record.uid, p_guild_id, v_credit_record.amt)
                ON CONFLICT (user_id, guild_id) DO UPDATE
                    SET balance = LEAST(p_max_balance, economy.balance + v_credit_record.amt);
                v_tax_shipped := v_tax_shipped + v_credit_record.amt;
            END IF;
        END LOOP;
    END IF;

    -- 3. Increment treasury
    IF p_treasury > 0 THEN
        UPDATE economy_guild_settings
        SET treasury_balance = treasury_balance + p_treasury,
            updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
        WHERE guild_id = p_guild_id;
    END IF;

    -- 4. Write ledger entries (best-effort within transaction)
    -- Main balance change
    INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, balance_before, balance_after, reason, created_at)
    VALUES (p_guild_id, p_user_id, p_user_id, 'work', p_delta, v_balance - p_delta, v_balance, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);

    -- Tax collected
    IF p_tax > 0 THEN
        INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, metadata, created_at)
        VALUES (p_guild_id, p_user_id, p_user_id, 'tax_collected', p_tax, 'tax_atomic_reward', jsonb_build_object('shipped', v_tax_shipped, 'treasury', p_treasury, 'discarded', p_discarded), EXTRACT(EPOCH FROM NOW())::BIGINT);
    END IF;

    -- Individual tax credits
    IF p_credits IS NOT NULL AND jsonb_array_length(p_credits) > 0 THEN
        FOR v_credit_record IN
            SELECT (elem->>'user_id')::TEXT AS uid, (elem->>'amount')::BIGINT AS amt
            FROM jsonb_array_elements(p_credits) AS elem
        LOOP
            IF v_credit_record.amt > 0 THEN
                INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
                VALUES (p_guild_id, v_credit_record.uid, p_user_id, 'tax_distributed', v_credit_record.amt, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);
            END IF;
        END LOOP;
    END IF;

    -- Treasury share
    IF p_treasury > 0 THEN
        INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
        VALUES (p_guild_id, NULL, p_user_id, 'treasury_deposit', p_treasury, 'tax_atomic_reward', EXTRACT(EPOCH FROM NOW())::BIGINT);
    END IF;

    -- 5. Record the completed balance in the reference table
    UPDATE economy_balance_references
    SET balance_after = v_balance
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_balance, v_tax_shipped, p_treasury, p_discarded;
END;
$$;

REVOKE ALL ON FUNCTION apply_economy_balance_with_tax_once(TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION apply_economy_balance_with_tax_once(TEXT, TEXT, TEXT, BIGINT, BIGINT, BIGINT, JSONB, BIGINT, BIGINT) TO service_role;

NOTIFY pgrst, 'reload schema';
