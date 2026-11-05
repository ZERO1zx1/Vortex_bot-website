"""Regression tests for Supabase client lifecycle during key probing/switching.

The startup key probe used to close every httpx pool the manager had created,
including the live client.  The bot then logged ``Supabase connected`` and every
query immediately failed with "Cannot send a request, as the client has been
closed."
"""

import pytest

from src.database import db_manager as db_module
from src.database.db_manager import SupabaseManager

SECRET_A = "sb_secret_" + "a" * 40
SECRET_B = "sb_secret_" + "b" * 40


class FakeClient:
    def __init__(self, key, http_client):
        self.key = key
        self.http_client = http_client


@pytest.fixture
def manager(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", SECRET_A)
    monkeypatch.setenv("SUPABASE_SECRET_KEY", SECRET_B)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    created = []

    def fake_create(url, key, options):
        client = FakeClient(key, options.httpx_client)
        created.append(client)
        return client

    monkeypatch.setattr(db_module, "create_client", fake_create)
    mgr = SupabaseManager()
    mgr.url = "https://example.supabase.co"
    mgr.key = SECRET_A
    mgr.created_clients = created
    return mgr


@pytest.mark.asyncio
async def test_probe_with_active_key_keeps_client_open(manager):
    async def probe(_table):
        return "OK"

    manager.probe_table = probe
    active = manager.connect()

    assert await manager.probe_best_key() == "SUPABASE_SERVICE_ROLE_KEY"
    assert manager.client is active
    assert not active.http_client.is_closed
    assert len(manager.created_clients) == 1


@pytest.mark.asyncio
async def test_probe_fallback_restores_active_client(manager):
    active = manager.connect()

    async def probe(_table):
        return "PERMISSION_DENIED" if manager.client is active else "OK"

    manager.probe_table = probe

    assert await manager.probe_best_key() == "SUPABASE_SECRET_KEY"
    assert manager.client is active
    assert not active.http_client.is_closed

    probe_client = manager.created_clients[-1]
    assert probe_client is not active
    assert probe_client.http_client.is_closed


def test_switch_key_closes_only_the_old_client(manager):
    old = manager.connect()

    assert manager.switch_key("SUPABASE_SECRET_KEY") is True
    new = manager.client

    assert new is not old
    assert old.http_client.is_closed
    assert not new.http_client.is_closed
    assert manager.key == SECRET_B


@pytest.mark.asyncio
async def test_close_releases_active_client(manager):
    active = manager.connect()

    await manager.close()

    assert manager.client is None
    assert active.http_client.is_closed
