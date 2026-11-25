from __future__ import annotations

import os

import asyncpg  # type: ignore[import-untyped]
import pytest

import config
from core.database import Database


async def test_fresh_supabase_schema_and_seed() -> None:
    test_url = os.getenv("AETHER_TEST_DATABASE_URL", "").strip()
    if not test_url:
        pytest.skip("AETHER_TEST_DATABASE_URL өгөөгүй")
    production_url = os.getenv("DATABASE_URL", "").strip()
    if production_url and test_url == production_url:
        pytest.fail("Integration test URL нь production DATABASE_URL байж болохгүй")

    connection = await asyncpg.connect(
        dsn=test_url, ssl="require", statement_cache_size=0
    )
    try:
        existing = await connection.fetchrow(
            "SELECT to_regclass('public.users') AS users, "
            "to_regclass('public.schema_migrations') AS migrations"
        )
        if existing["users"] is not None or existing["migrations"] is not None:
            pytest.fail("Integration test-д зөвхөн шинэ, хоосон database ашиглана")
    finally:
        await connection.close()

    async with Database(test_url, migrations_dir=config.MIGRATIONS_DIR) as db:
        assert await db.fetchval("SELECT COUNT(*) FROM shop_items") == 6
        assert (
            await db.fetchval(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'users'"
            )
            == 1
        )
