from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest_asyncio

from tests.fakes.database import SqliteTestDatabase


@pytest_asyncio.fixture
async def db(tmp_path: Path) -> AsyncIterator[SqliteTestDatabase]:
    database = SqliteTestDatabase(tmp_path / "aether-test.db")
    await database.connect()
    try:
        yield database
    finally:
        await database.close()
