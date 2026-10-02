CREATE TABLE IF NOT EXISTS poker_pending_payouts (
    channel_id TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    host_id TEXT NOT NULL,
    intent TEXT NOT NULL DEFAULT 'settlement' CHECK (intent IN ('refund', 'settlement')),
    amount BIGINT NOT NULL CHECK (amount > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMPTZ,
    PRIMARY KEY (channel_id, user_id)
);

ALTER TABLE poker_pending_payouts
    ADD COLUMN IF NOT EXISTS intent TEXT NOT NULL DEFAULT 'settlement';
ALTER TABLE poker_pending_payouts
    ADD COLUMN IF NOT EXISTS settled_at TIMESTAMPTZ;
DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'poker_pending_payouts_intent_check'
          AND conrelid = 'poker_pending_payouts'::regclass
    ) THEN
        ALTER TABLE poker_pending_payouts
            ADD CONSTRAINT poker_pending_payouts_intent_check
            CHECK (intent IN ('refund', 'settlement'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_poker_pending_payouts_channel_guild
    ON poker_pending_payouts (channel_id, guild_id);
CREATE INDEX IF NOT EXISTS idx_poker_pending_payouts_unsettled
    ON poker_pending_payouts (channel_id, guild_id)
    WHERE settled_at IS NULL;

ALTER TABLE poker_pending_payouts ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE poker_pending_payouts TO service_role;

CREATE OR REPLACE FUNCTION begin_poker_table(p_channel_id TEXT, p_guild_id TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND settled_at IS NULL
    ) THEN
        RAISE EXCEPTION 'Unsettled poker obligation exists';
    END IF;
    DELETE FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id;
    RETURN TRUE;
END;
$$;
COMMENT ON FUNCTION begin_poker_table(TEXT, TEXT) IS
    'Fails if unsettled obligations exist; otherwise removes settled history. It creates no persistent lock row.';

CREATE OR REPLACE FUNCTION charge_poker_buyin(
    p_channel_id TEXT, p_guild_id TEXT, p_user_id TEXT,
    p_host_id TEXT, p_amount BIGINT
) RETURNS BIGINT
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_marker BIGINT;
BEGIN
    IF p_amount <= 0 THEN RAISE EXCEPTION 'Invalid poker buy-in'; END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND intent = 'settlement'
    ) THEN
        RAISE EXCEPTION 'Poker settlement already prepared';
    END IF;
    INSERT INTO poker_pending_payouts(channel_id, guild_id, user_id, host_id, amount, intent)
    VALUES (p_channel_id, p_guild_id, p_user_id, p_host_id, p_amount, 'refund')
    ON CONFLICT (channel_id, user_id) DO NOTHING
    RETURNING amount INTO v_marker;
    IF v_marker IS NULL THEN RAISE EXCEPTION 'Poker buy-in already charged'; END IF;

    UPDATE economy SET balance = balance - p_amount
    WHERE user_id = p_user_id AND guild_id = p_guild_id AND balance >= p_amount;
    IF NOT FOUND THEN RAISE EXCEPTION 'Insufficient poker balance'; END IF;
    RETURN p_amount;
END;
$$;

DROP FUNCTION IF EXISTS prepare_poker_settlement(TEXT, TEXT, TEXT, JSONB);
CREATE OR REPLACE FUNCTION prepare_poker_settlement(
    p_channel_id TEXT, p_guild_id TEXT, p_host_id TEXT,
    p_expected_total BIGINT, p_payouts JSONB
) RETURNS INTEGER
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE v_count INTEGER; v_plan_total BIGINT; v_refund_total BIGINT;
BEGIN
    IF p_expected_total <= 0 THEN
        RAISE EXCEPTION 'Poker expected total must be positive';
    END IF;
    IF jsonb_typeof(p_payouts) <> 'array' OR jsonb_array_length(p_payouts) = 0 THEN
        RAISE EXCEPTION 'Poker settlement plan is empty';
    END IF;
    IF EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_payouts) AS item
        WHERE jsonb_typeof(item) <> 'object'
           OR NULLIF(BTRIM(item->>'user_id'), '') IS NULL
           OR COALESCE(item->>'amount', '') !~ '^[0-9]+$'
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains an invalid payout';
    END IF;
    IF EXISTS (
        SELECT 1 FROM jsonb_array_elements(p_payouts) AS item
        WHERE (item->>'amount')::BIGINT <= 0
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains an invalid payout';
    END IF;
    IF (
        SELECT COUNT(*) FROM jsonb_array_elements(p_payouts)
    ) <> (
        SELECT COUNT(DISTINCT item->>'user_id') FROM jsonb_array_elements(p_payouts) AS item
    ) THEN
        RAISE EXCEPTION 'Poker settlement plan contains duplicate users';
    END IF;
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    IF EXISTS (
        SELECT 1 FROM poker_pending_payouts
        WHERE channel_id = p_channel_id AND guild_id = p_guild_id
          AND settled_at IS NULL AND host_id <> p_host_id
    ) THEN
        RAISE EXCEPTION 'Poker settlement contains another host';
    END IF;
    SELECT COALESCE(SUM((item->>'amount')::BIGINT), 0) INTO v_plan_total
    FROM jsonb_array_elements(p_payouts) AS item;
    SELECT COALESCE(SUM(amount), 0) INTO v_refund_total
    FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id
      AND host_id = p_host_id AND intent = 'refund' AND settled_at IS NULL;
    IF v_plan_total <> p_expected_total OR v_refund_total <> p_expected_total THEN
        RAISE EXCEPTION 'Poker settlement total mismatch: plan %, committed %, expected %',
            v_plan_total, v_refund_total, p_expected_total;
    END IF;
    DELETE FROM poker_pending_payouts
    WHERE channel_id = p_channel_id AND guild_id = p_guild_id
      AND settled_at IS NULL;
    INSERT INTO poker_pending_payouts(channel_id, guild_id, user_id, host_id, amount, intent)
    SELECT p_channel_id, p_guild_id, item->>'user_id', p_host_id,
           (item->>'amount')::BIGINT, 'settlement'
    FROM jsonb_array_elements(p_payouts) AS item
    WHERE (item->>'amount')::BIGINT > 0;
    GET DIAGNOSTICS v_count = ROW_COUNT;
    IF v_count = 0 THEN RAISE EXCEPTION 'Poker settlement plan has no payouts'; END IF;
    RETURN v_count;
END;
$$;

REVOKE ALL ON FUNCTION charge_poker_buyin(TEXT, TEXT, TEXT, TEXT, BIGINT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION charge_poker_buyin(TEXT, TEXT, TEXT, TEXT, BIGINT) TO service_role;
REVOKE ALL ON FUNCTION begin_poker_table(TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION begin_poker_table(TEXT, TEXT) TO service_role;
REVOKE ALL ON FUNCTION prepare_poker_settlement(TEXT, TEXT, TEXT, BIGINT, JSONB) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION prepare_poker_settlement(TEXT, TEXT, TEXT, BIGINT, JSONB) TO service_role;

CREATE OR REPLACE FUNCTION settle_poker_payout(
    p_channel_id TEXT,
    p_guild_id TEXT,
    p_user_id TEXT
) RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_amount BIGINT;
    v_row_guild_id TEXT;
BEGIN
    PERFORM pg_advisory_xact_lock(hashtextextended(p_channel_id || ':' || p_guild_id, 0));
    UPDATE poker_pending_payouts
    SET settled_at = NOW()
    WHERE channel_id = p_channel_id
      AND guild_id = p_guild_id
      AND user_id = p_user_id
      AND settled_at IS NULL
    RETURNING amount, guild_id INTO v_amount, v_row_guild_id;

    IF v_amount IS NULL THEN
        RETURN 0;
    END IF;

    UPDATE economy
    SET balance = COALESCE(balance, 0) + v_amount
    WHERE user_id = p_user_id AND guild_id = v_row_guild_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Economy account not found for user % guild %', p_user_id, p_guild_id;
    END IF;

    RETURN v_amount;
END;
$$;

REVOKE ALL ON FUNCTION settle_poker_payout(TEXT, TEXT, TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION settle_poker_payout(TEXT, TEXT, TEXT) TO service_role;

NOTIFY pgrst, 'reload schema';
