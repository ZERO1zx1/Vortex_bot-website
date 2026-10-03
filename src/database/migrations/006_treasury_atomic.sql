-- ============================================================================
-- AETHER: Atomic treasury payments (2026-10-02)
-- ----------------------------------------------------------------------------
-- Creates treasury_pay_once RPC that atomically:
--   1. Claims a reference (idempotency key) in treasury_payments
--   2. Validates treasury has sufficient balance
--   3. Debits treasury_balance
--   4. Credits recipients (equal split, remainder to first)
--   5. Writes ledger entries for all mutations
-- All in a single PostgreSQL transaction.
--
-- Idempotency: same reference + identical payload → returns original result
--              same reference + different payload → raises exception
--              reference already applied → returns committed result, no re-credit
--
-- This migration is idempotent and safe to run on existing projects.
-- ============================================================================

-- 1. Idempotency table for treasury payments
CREATE TABLE IF NOT EXISTS treasury_payments (
    reference TEXT PRIMARY KEY CHECK (char_length(reference) BETWEEN 1 AND 200),
    guild_id TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    amount BIGINT NOT NULL,
    recipient_ids BIGINT[] NOT NULL,
    reason TEXT,
    treasury_after BIGINT,
    credits JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_treasury_payments_created_at
    ON treasury_payments (created_at);

ALTER TABLE treasury_payments ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE ON TABLE treasury_payments TO service_role;

-- 2. Atomic RPC: treasury debit + recipient credits in one transaction
CREATE OR REPLACE FUNCTION treasury_pay_once(
    p_reference TEXT,
    p_guild_id TEXT,
    p_actor_id TEXT,
    p_amount BIGINT,
    p_recipient_ids BIGINT[],
    p_reason TEXT
) RETURNS TABLE(
    applied BOOLEAN,
    treasury_after BIGINT,
    credits JSONB
) LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_claimed_count BIGINT;
    v_existing treasury_payments%ROWTYPE;
    v_treasury_before BIGINT;
    v_treasury_after BIGINT;
    v_recipient_count INT;
    v_share BIGINT;
    v_remainder BIGINT;
    v_credit_json JSONB := '[]'::JSONB;
    v_uid BIGINT;
    v_amt BIGINT;
    v_idx INT := 0;
BEGIN
    -- Validate inputs
    IF p_reference IS NULL OR char_length(p_reference) NOT BETWEEN 1 AND 200 THEN
        RAISE EXCEPTION 'reference must contain 1-200 characters';
    END IF;
    IF p_amount <= 0 THEN
        RAISE EXCEPTION 'amount must be positive';
    END IF;
    IF p_recipient_ids IS NULL OR array_length(p_recipient_ids, 1) IS NULL THEN
        RAISE EXCEPTION 'recipient_ids must be a non-empty array';
    END IF;
    v_recipient_count := array_length(p_recipient_ids, 1);
    IF v_recipient_count > 50 THEN
        RAISE EXCEPTION 'maximum 50 recipients per payment';
    END IF;
    IF EXISTS (
        SELECT 1
        FROM unnest(p_recipient_ids) AS recipient_id
        GROUP BY recipient_id
        HAVING COUNT(*) > 1
    ) THEN
        RAISE EXCEPTION 'recipient_ids must be unique';
    END IF;
    IF p_amount > 100000000000 THEN
        RAISE EXCEPTION 'amount exceeds maximum (100B)';
    END IF;
    IF char_length(COALESCE(p_reason, '')) > 200 THEN
        RAISE EXCEPTION 'reason exceeds maximum length (200)';
    END IF;

    -- Claim the reference (idempotency key)
    INSERT INTO treasury_payments (reference, guild_id, actor_id, amount, recipient_ids, reason)
    VALUES (p_reference, p_guild_id, p_actor_id, p_amount, p_recipient_ids, p_reason)
    ON CONFLICT (reference) DO NOTHING;
    GET DIAGNOSTICS v_claimed_count = ROW_COUNT;

    IF v_claimed_count = 0 THEN
        -- Reference already exists: verify payload matches, return committed result
        SELECT * INTO v_existing
        FROM treasury_payments
        WHERE reference = p_reference;

        IF v_existing.guild_id IS DISTINCT FROM p_guild_id
           OR v_existing.actor_id IS DISTINCT FROM p_actor_id
           OR v_existing.amount IS DISTINCT FROM p_amount
           OR v_existing.recipient_ids IS DISTINCT FROM p_recipient_ids
           OR v_existing.reason IS DISTINCT FROM p_reason THEN
            RAISE EXCEPTION 'reference % was already used with a different payload', p_reference;
        END IF;
        IF v_existing.treasury_after IS NULL THEN
            RAISE EXCEPTION 'reference % has no completed treasury result', p_reference;
        END IF;

        -- Return the originally committed result (no re-credit)
        RETURN QUERY SELECT FALSE, v_existing.treasury_after, v_existing.credits;
        RETURN;
    END IF;

    -- Check treasury balance and debit atomically
    UPDATE economy_guild_settings
    SET treasury_balance = treasury_balance - p_amount,
        updated_at = EXTRACT(EPOCH FROM NOW())::BIGINT
    WHERE guild_id = p_guild_id
      AND treasury_balance >= p_amount
    RETURNING treasury_balance INTO v_treasury_after;

    IF v_treasury_after IS NULL THEN
        RAISE EXCEPTION 'insufficient treasury balance for guild %', p_guild_id;
    END IF;

    -- Credit recipients (equal split, remainder to first)
    v_share := p_amount / v_recipient_count;
    v_remainder := p_amount % v_recipient_count;

    FOR v_idx IN 0 .. v_recipient_count - 1 LOOP
        v_uid := p_recipient_ids[v_idx + 1];
        v_amt := v_share + CASE WHEN v_idx = 0 THEN v_remainder ELSE 0 END;

        IF v_amt > 0 THEN
            INSERT INTO economy (user_id, guild_id, balance)
            VALUES (v_uid::TEXT, p_guild_id, v_amt)
            ON CONFLICT (user_id, guild_id) DO UPDATE
                SET balance = economy.balance + v_amt;

            v_credit_json := v_credit_json || jsonb_build_object('user_id', v_uid, 'amount', v_amt);
        END IF;
    END LOOP;

    -- Write ledger entries
    -- Treasury payment (debit)
    INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, metadata, created_at)
    VALUES (p_guild_id, NULL, p_actor_id, 'treasury_payment', -p_amount, p_reason, to_jsonb(p_recipient_ids), EXTRACT(EPOCH FROM NOW())::BIGINT);

    -- Individual payouts
    FOR v_idx IN 0 .. v_recipient_count - 1 LOOP
        v_uid := p_recipient_ids[v_idx + 1];
        v_amt := v_share + CASE WHEN v_idx = 0 THEN v_remainder ELSE 0 END;

        IF v_amt > 0 THEN
            INSERT INTO economy_ledger (guild_id, user_id, actor_id, transaction_type, amount, reason, created_at)
            VALUES (p_guild_id, v_uid::TEXT, p_actor_id, 'treasury_payout', v_amt, p_reason, EXTRACT(EPOCH FROM NOW())::BIGINT);
        END IF;
    END LOOP;

    -- Record completion
    UPDATE treasury_payments
    SET treasury_after = v_treasury_after,
        credits = v_credit_json
    WHERE reference = p_reference;

    RETURN QUERY SELECT TRUE, v_treasury_after, v_credit_json;
END;
$$;

REVOKE ALL ON FUNCTION treasury_pay_once(TEXT, TEXT, TEXT, BIGINT, BIGINT[], TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION treasury_pay_once(TEXT, TEXT, TEXT, BIGINT, BIGINT[], TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
