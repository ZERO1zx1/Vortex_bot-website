from pathlib import Path

from utils.cog_loader import discover_cogs


def test_discovers_every_public_cog(tmp_path: Path):
    (tmp_path / "economy.py").write_text("", encoding="utf-8")
    (tmp_path / "admin.py").write_text("", encoding="utf-8")
    (tmp_path / "_private.py").write_text("", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("", encoding="utf-8")

    assert discover_cogs(tmp_path) == ["admin", "economy"]


def test_missing_directory_is_actionable(tmp_path: Path):
    missing = tmp_path / "missing"
    try:
        discover_cogs(missing)
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("missing cog directory should fail")
