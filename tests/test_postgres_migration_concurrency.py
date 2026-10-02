"""Real PostgreSQL checks for the atomic payout/idempotency migrations.

The database named by ``AETHER_TEST_POSTGRES_DSN`` must be disposable: this
module recreates the small set of tables/functions it owns. GitHub Actions
provides a fresh PostgreSQL service. Local runs skip this module when no DSN is
configured.
"""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

DSN = os.getenv("AETHER_TEST_POSTGRES_DSN")
if not DSN:
    pytest.skip(
        "AETHER_TEST_POSTGRES_DSN is not configured",
        allow_module_level=True,
    )

psycopg = pytest.importorskip("psycopg")
MIGRATIONS = Path(__file__).resolve().parents[1] / "src" / "database" / "migrations"


@pytest.fixture(scope="module", autouse=True)
def migrated_database():
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute("DROP FUNCTION IF EXISTS apply_economy_balance_once(TEXT, TEXT, TEXT, BIGINT, BIGINT)")
        conn.execute("DROP FUNCTION IF EXISTS settle_poker_payout(TEXT, TEXT, TEXT)")
        conn.execute("DROP FUNCTION IF EXISTS prepare_poker_settlement(TEXT, TEXT, TEXT, BIGINT, JSONB)")
        conn.execute("DROP FUNCTION IF EXISTS charge_poker_buyin(TEXT, TEXT, TEXT, TEXT, BIGINT)")
        conn.execute("DROP FUNCTION IF EXISTS begin_poker_table(TEXT, TEXT)")
        conn.execute("DROP TABLE IF EXISTS economy_balance_references")
        conn.execute("DROP TABLE IF EXISTS poker_pending_payouts")
        conn.execute("DROP TABLE IF EXISTS economy")
        conn.execute(
            """
            DO $$
            BEGIN
                CREATE ROLE service_role NOLOGIN;
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END
            $$
            """
        )
        conn.execute(
            """
            CREATE TABLE economy (
                user_id TEXT NOT NULL,
                guild_id TEXT NOT NULL,
                balance BIGINT DEFAULT 1000,
                PRIMARY KEY (user_id, guild_id)
            )
            """
        )
        conn.execute(
            (MIGRATIONS / "002_poker_pending_payouts.sql").read_text(encoding="utf-8")
        )
        conn.execute(
            (MIGRATIONS / "003_economy_balance_idempotency.sql").read_text(encoding="utf-8")
        )
    yield


def _run_balance_once(barrier, reference, delta):
    with psycopg.connect(DSN) as conn:
        barrier.wait()
        row = conn.execute(
            """
            SELECT applied, balance
            FROM apply_economy_balance_once(%s, %s, %s, %s, %s)
            """,
            (reference, "7", "5", delta, 100_000_000),
        ).fetchone()
        conn.commit()
        return row


def test_same_reference_concurrent_calls_credit_once():
    with psycopg.connect(DSN) as conn:
        conn.execute(
            "INSERT INTO economy (user_id, guild_id, balance) VALUES (%s, %s, %s)",
            ("7", "5", 1_000),
        )
        conn.commit()

    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_run_balance_once, barrier, "reward:concurrent", 100)
            for _ in range(2)
        ]
        results = [future.result(timeout=10) for future in futures]

    assert sorted(results) == [(False, 1_100), (True, 1_100)]
    with psycopg.connect(DSN) as conn:
        assert conn.execute(
            "SELECT balance FROM economy WHERE user_id = '7' AND guild_id = '5'"
        ).fetchone() == (1_100,)
        assert conn.execute(
            "SELECT count(*) FROM economy_balance_references WHERE reference = %s",
            ("reward:concurrent",),
        ).fetchone() == (1,)


def test_same_reference_with_different_payload_fails_closed():
    with psycopg.connect(DSN) as conn, pytest.raises(psycopg.Error, match="different payload"):
        conn.execute(
            "SELECT * FROM apply_economy_balance_once(%s, %s, %s, %s, %s)",
            ("reward:concurrent", "7", "5", 101, 100_000_000),
        ).fetchone()


def _settle_poker_once(barrier):
    with psycopg.connect(DSN) as conn:
        barrier.wait()
        amount = conn.execute(
            "SELECT settle_poker_payout(%s, %s, %s)",
            ("channel-1", "5", "9"),
        ).fetchone()[0]
        conn.commit()
        return amount


def test_poker_payout_concurrent_settlement_credits_once():
    with psycopg.connect(DSN) as conn:
        conn.execute(
            "INSERT INTO economy (user_id, guild_id, balance) VALUES (%s, %s, %s)",
            ("9", "5", 1_000),
        )
        conn.execute(
            """
            INSERT INTO poker_pending_payouts
                (channel_id, guild_id, user_id, host_id, amount)
            VALUES (%s, %s, %s, %s, %s)
            """,
            ("channel-1", "5", "9", "1", 250),
        )
        conn.commit()

    barrier = threading.Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_settle_poker_once, barrier) for _ in range(2)]
        results = [future.result(timeout=10) for future in futures]

    assert sorted(results) == [0, 250]
    with psycopg.connect(DSN) as conn:
        assert conn.execute(
            "SELECT balance FROM economy WHERE user_id = '9' AND guild_id = '5'"
        ).fetchone() == (1_250,)
        assert conn.execute(
            "SELECT count(*) FROM poker_pending_payouts WHERE channel_id = %s AND settled_at IS NULL",
            ("channel-1",),
        ).fetchone() == (0,)
        assert conn.execute(
            "SELECT count(*) FROM poker_pending_payouts WHERE channel_id = %s AND settled_at IS NOT NULL",
            ("channel-1",),
        ).fetchone() == (1,)


def test_charge_is_idempotent_and_rejected_after_settlement_prepare():
    with psycopg.connect(DSN) as conn:
        conn.execute(
            "INSERT INTO economy (user_id, guild_id, balance) VALUES (%s, %s, %s)",
            ("10", "5", 1_000),
        )
        conn.commit()

    with psycopg.connect(DSN) as conn:
        assert conn.execute(
            "SELECT begin_poker_table(%s, %s)", ("channel-2", "5")
        ).fetchone() == (True,)
        assert conn.execute(
            "SELECT charge_poker_buyin(%s, %s, %s, %s, %s)",
            ("channel-2", "5", "10", "10", 100),
        ).fetchone() == (100,)
        conn.commit()

    with psycopg.connect(DSN) as conn, pytest.raises(psycopg.Error, match="already charged"):
        conn.execute(
            "SELECT charge_poker_buyin(%s, %s, %s, %s, %s)",
            ("channel-2", "5", "10", "10", 100),
        ).fetchone()
    with psycopg.connect(DSN) as conn:
        assert conn.execute(
            "SELECT balance FROM economy WHERE user_id = '10' AND guild_id = '5'"
        ).fetchone() == (900,)

    # Use a clean committed round to verify that no late buy-in can appear
    # after the refund markers have atomically become settlement markers.
    with psycopg.connect(DSN) as conn:
        conn.execute(
            "SELECT prepare_poker_settlement(%s, %s, %s, %s, %s::jsonb)",
            ("channel-2", "5", "10", 100, '[{"user_id":"10","amount":100}]'),
        )
        conn.commit()

    with psycopg.connect(DSN) as conn, pytest.raises(psycopg.Error, match="settlement already prepared"):
        conn.execute(
            "SELECT charge_poker_buyin(%s, %s, %s, %s, %s)",
            ("channel-2", "5", "11", "10", 100),
        ).fetchone()


@pytest.mark.parametrize("bad_amount", ["abc", "   ", "-1", "0"])
def test_prepare_rejects_malformed_amount_with_controlled_error(bad_amount):
    with psycopg.connect(DSN) as conn, pytest.raises(psycopg.Error, match="contains an invalid payout"):
        conn.execute(
            "SELECT prepare_poker_settlement(%s, %s, %s, %s, %s::jsonb)",
            (
                "channel-bad", "5", "1", 100,
                json.dumps([{"user_id": "1", "amount": bad_amount}]),
            ),
        ).fetchone()
