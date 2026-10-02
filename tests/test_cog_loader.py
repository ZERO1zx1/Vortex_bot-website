from pathlib import Path

from src.utils.cog_loader import ACTIVE_COGS, discover_cogs


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


def test_every_active_cog_has_a_module():
    cogs_dir = Path(__file__).resolve().parents[1] / "src" / "cogs"

    assert set(discover_cogs(cogs_dir, ACTIVE_COGS)) == set(ACTIVE_COGS)


def test_help_loads_after_feature_cogs():
    cogs_dir = Path(__file__).resolve().parents[1] / "src" / "cogs"

    assert discover_cogs(cogs_dir, ACTIVE_COGS)[-1] == "help"


def test_level_admin_loads_after_leveling_and_before_help():
    cogs_dir = Path(__file__).resolve().parents[1] / "src" / "cogs"
    names = discover_cogs(cogs_dir, ACTIVE_COGS)

    assert "level_admin" in ACTIVE_COGS
    assert names.index("leveling") < names.index("level_admin") < names.index("help")
