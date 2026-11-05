"""Regression tests for Supabase server-key resolution.

The bot must never run on an anon/publishable key: that is the 42501 root
cause.  ``SUPABASE_SERVICE_ROLE_KEY`` / ``SUPABASE_SECRET_KEY`` /
``SUPABASE_KEY`` are all *server* names, so holding an anon value in any of
them is a configuration error even though the bot tolerates it.
"""

import base64
import json

import pytest

from src.core import config as config_module
from src.core.config import (
    describe_key,
    is_server_level_key,
    pick_server_supabase_key,
    report_key_mismatches_once,
    supabase_key_mismatches,
)

ALL_ENVS = config_module.SUPABASE_SERVER_ROLE_ENVS


def _jwt(role: str) -> str:
    """Build an unsigned JWT whose payload carries ``role``."""
    def segment(obj):
        raw = json.dumps(obj).encode()
        return base64.urlsafe_b64encode(raw).decode().rstrip("=")

    return f"{segment({'alg': 'HS256'})}.{segment({'role': role})}.sig"


ANON_JWT = _jwt("anon")
AUTHENTICATED_JWT = _jwt("authenticated")
SERVICE_JWT = _jwt("service_role")
SECRET_KEY = "sb_secret_" + "a" * 40
PUBLISHABLE_KEY = "sb_publishable_" + "b" * 40


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for env in ALL_ENVS:
        monkeypatch.delenv(env, raising=False)
    # Reset the once-per-process latch so each test sees a fresh report.
    monkeypatch.setattr(config_module, "_mismatch_reported", False)
    yield


# ── classification ─────────────────────────────────────────────

@pytest.mark.parametrize("key", [SECRET_KEY, SERVICE_JWT])
def test_server_level_keys_accepted(key):
    assert is_server_level_key(key)


@pytest.mark.parametrize("key", [ANON_JWT, AUTHENTICATED_JWT, PUBLISHABLE_KEY, "", "not-a-jwt"])
def test_non_server_keys_rejected(key):
    assert not is_server_level_key(key)


def test_describe_key_never_echoes_the_secret():
    for key in (SECRET_KEY, SERVICE_JWT, ANON_JWT, PUBLISHABLE_KEY):
        described = describe_key(key)
        assert key not in described
        assert len(described) < 40


# ── selection ──────────────────────────────────────────────────

def test_picks_secret_key_over_every_anon(monkeypatch):
    # The real-world .env: server-named vars hold publishable keys.
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", ANON_JWT)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", SECRET_KEY)
    monkeypatch.setenv("SUPABASE_KEY", PUBLISHABLE_KEY)

    assert pick_server_supabase_key() == SECRET_KEY


def test_never_returns_an_anon_value(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", ANON_JWT)
    monkeypatch.setenv("SUPABASE_KEY", PUBLISHABLE_KEY)

    assert pick_server_supabase_key() == ""


def test_service_role_jwt_is_used_when_it_is_genuine(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", SERVICE_JWT)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", SECRET_KEY)

    assert pick_server_supabase_key() == SERVICE_JWT


# ── mismatch reporting ──────────────────────────────────────────

def test_mismatch_is_reported_for_server_named_anon_vars(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", ANON_JWT)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", SECRET_KEY)
    monkeypatch.setenv("SUPABASE_KEY", PUBLISHABLE_KEY)

    reported = report_key_mismatches_once()

    assert {env for env, _ in reported} == {"SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_KEY"}
    assert all("anon" in role or "publishable" in role for _, role in reported)


def test_no_report_when_every_var_is_a_server_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", SERVICE_JWT)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", SECRET_KEY)

    assert report_key_mismatches_once() == []
    assert supabase_key_mismatches() == []


def test_report_is_emitted_only_once_per_process(monkeypatch):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", ANON_JWT)

    assert len(report_key_mismatches_once()) == 1
    assert report_key_mismatches_once() == []
    assert supabase_key_mismatches()  # the underlying state is still detectable


def test_report_logs_once_and_never_echoes_values(monkeypatch, caplog):
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", ANON_JWT)

    with caplog.at_level("ERROR"):
        report_key_mismatches_once()

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "SUPABASE_SERVICE_ROLE_KEY" in message
    assert ANON_JWT not in message