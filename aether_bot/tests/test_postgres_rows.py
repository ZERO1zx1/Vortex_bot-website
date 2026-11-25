from __future__ import annotations

from datetime import UTC, datetime

from repositories.log_repo import CasinoLogRow


def test_casino_log_normalizes_postgresql_timestamp_for_ui() -> None:
    row = CasinoLogRow.from_row(
        {
            "log_id": 1,
            "user_id": 2,
            "game": "slots",
            "bet": 100,
            "payout": 200,
            "outcome": "win",
            "detail": None,
            "created_at": datetime(2026, 11, 25, 8, 30, tzinfo=UTC),
        }
    )
    assert row.created_at == "2026-11-25 08:30:00"
    assert row.created_at[11:16] == "08:30"
