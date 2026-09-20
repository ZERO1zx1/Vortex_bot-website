import time
from types import SimpleNamespace

import pytest

from src.database.db_manager import (
    _TableErrorTracker,
    classify_supabase_error,
    DatabasePermissionError,
    DatabaseSchemaError,
    DatabaseUnavailableError,
)


class _FakeErr:
    """Exception-like object with real attribute semantics for ``str()``."""

    def __init__(self, code=None, status=None, message: str = ""):
        self.code = code
        self.status_code = status
        self.status = None
        self._message = message

    def __str__(self):
        return self._message


def _err(code=None, status=None, message: str = ""):
    return _FakeErr(code=code, status=status, message=message)


def test_pgrst205_maps_to_schema_error():
    exc = _err(code="PGRST205", message="relation does not exist")
    assert isinstance(classify_supabase_error(exc), DatabaseSchemaError)


def test_http_404_maps_to_schema_error():
    exc = _err(status=404, message="not found")
    assert isinstance(classify_supabase_error(exc), DatabaseSchemaError)


def test_42501_maps_to_permission_error():
    exc = _err(code="42501", message="permission denied for table economy")
    assert isinstance(classify_supabase_error(exc), DatabasePermissionError)


def test_5xx_maps_to_unavailable():
    exc = _err(code="504", message="gateway timeout")
    assert isinstance(classify_supabase_error(exc), DatabaseUnavailableError)


def test_connection_error_maps_to_unavailable():
    assert isinstance(classify_supabase_error(TimeoutError("took too long")),
                      DatabaseUnavailableError)


def test_unknown_code_passes_through_unchanged():
    exc = _err(code="23505", message="duplicate key")
    # Unknown errors are returned as-is so genuine bugs keep their identity.
    assert classify_supabase_error(exc) is exc


def test_classify_from_exception_strings_only():
    """Real supabase/APIError objects often surface text like '{"code":"42501"}'
    without a .code attribute; string subclassing must still classify."""
    exc = _err(message='{"code":"42501","message":"permission denied for table levels"}')
    exc.code = None
    assert isinstance(classify_supabase_error(exc), DatabasePermissionError)


class TestTableErrorTracker:
    def test_first_failure_logs_full_guidance_then_rest_are_silent(self, caplog):
        tracker = _TableErrorTracker(logger_name="aether.db.test")
        caplog.set_level("ERROR", logger="aether.db.test")

        with caplog.at_level("ERROR", logger="aether.db.test"):
            tracker.report("staff_members", "PGRST205")
            tracker.report("staff_members", "PGRST205")
            tracker.report("staff_members", "PGRST205")

        error_lines = [r for r in caplog.records if r.name == "aether.db.test"]
        # 1 detailed log + 0 repeats within the dedup window
        assert len(error_lines) == 1
        assert "000_aether_complete.sql" in error_lines[0].getMessage()

    def test_window_elapse_emits_compact_summary(self, caplog, monkeypatch):
        tracker = _TableErrorTracker(logger_name="aether.db.test")
        caplog.set_level("ERROR", logger="aether.db.test")

        monotonic_ticks = iter([100.0, 100.0, 100.5, 720.0])

        def fake_monotonic():
            return next(monotonic_ticks)

        monkeypatch.setattr("src.database.db_manager.time.monotonic", fake_monotonic)

        with caplog.at_level("ERROR", logger="aether.db.test"):
            tracker.report("counting_config", "denied")   # window start, full guidance
        caplog.clear()

        with caplog.at_level("ERROR", logger="aether.db.test"):
            tracker.report("counting_config", "denied")   # repeat 1 (silent)
            tracker.report("counting_config", "denied")   # repeat 2 (silent)
            tracker.report("counting_config", "denied")   # window elapsed -> summary

        messages = [r.getMessage() for r in caplog.records]
        repeated = [m for m in messages if "repeat error(s)" in m]
        assert len(repeated) == 1
        assert "2 repeat error(s)" in repeated[0]
        # no full-traceback-style guidance spam for repeats
        assert all("000_aether_complete.sql" not in m for m in repeated)

    def test_tables_log_independently(self, caplog):
        tracker = _TableErrorTracker(logger_name="aether.db.test")
        caplog.set_level("ERROR", logger="aether.db.test")

        with caplog.at_level("ERROR", logger="aether.db.test"):
            tracker.report("table_a", "PGRST205")
            tracker.report("table_b", "42501")
            tracker.report("table_a", "PGRST205")

        names = {r.getMessage().split("'")[1] for r in caplog.records if r.name == "aether.db.test"}
        assert names == {"table_a", "table_b"}
