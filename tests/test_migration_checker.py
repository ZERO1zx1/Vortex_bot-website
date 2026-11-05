from tools.check_migration_applied import migration_is_complete


def test_checker_covers_every_bootstrap_table():
    import re
    from pathlib import Path

    from tools.check_migration_applied import ALL_TABLES

    sql = (Path(__file__).resolve().parents[1] / "src/database/migrations/000_aether_complete.sql").read_text(encoding="utf-8")
    tables = set(re.findall(r"^\s*CREATE TABLE IF NOT EXISTS (\w+)", sql, re.IGNORECASE | re.MULTILINE))
    assert tables <= set(ALL_TABLES), f"Unchecked tables: {tables - set(ALL_TABLES)}"


def test_migration_checker_requires_every_table_to_be_observed_ok():
    assert migration_is_complete(
        {"OK": 3, "MISSING": 0, "PERMISSION": 0, "UNAVAILABLE": 0, "ERROR": 0},
        3,
    )


def test_migration_checker_fails_closed_when_database_is_unavailable():
    assert not migration_is_complete(
        {"OK": 0, "MISSING": 0, "PERMISSION": 0, "UNAVAILABLE": 3, "ERROR": 0},
        3,
    )
