from __future__ import annotations

from datetime import UTC, datetime

from utils.time_utils import from_db, to_db


def test_parse_sqlite_naive_timestamp() -> None:
    moment = from_db("2026-11-18 14:00:00")
    assert moment == datetime(2026, 11, 18, 14, 0, tzinfo=UTC)


def test_parse_z_timestamp() -> None:
    assert from_db("2026-11-18T14:00:00Z") is not None


def test_parse_positive_offset() -> None:
    moment = from_db("2026-11-18 14:00:00+08:00")
    assert moment == datetime(2026, 11, 18, 6, 0, tzinfo=UTC)


def test_parse_negative_offset() -> None:
    moment = from_db("2026-11-18 14:00:00-05:00")
    assert moment == datetime(2026, 11, 18, 19, 0, tzinfo=UTC)


def test_invalid_timestamp_returns_none() -> None:
    assert from_db("not-a-date") is None


def test_to_db_normalizes_to_utc() -> None:
    moment = datetime(2026, 11, 18, 14, 0, tzinfo=UTC)
    assert to_db(moment) == "2026-11-18 14:00:00"
