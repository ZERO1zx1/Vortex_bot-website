"""S17  Staff KPI data disclosure.

`/staff_counts` and `/staff_status` carried no permission check and replied
without `ephemeral=True`, so any member could run them and the full staff
performance table -- message counts, voice hours, moderation actions, tickets
closed and the computed KPI for every registered staff member -- was posted
publicly into the channel. `staff_setup` in the same file already required
`administrator=True`; these two were the gap.
"""

import ast
import pathlib

import pytest

MOD = pathlib.Path("src/cogs/admin/moderation.py")


def _command_node(name: str):
    tree = ast.parse(MOD.read_bytes().decode("utf-8-sig", errors="replace"))
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for fn in cls.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in fn.decorator_list:
                if f"name='{name}'" in ast.unparse(dec) or f'name="{name}"' in ast.unparse(dec):
                    return fn
    return None


def _decorators(fn) -> list[str]:
    return [ast.unparse(d) for d in fn.decorator_list]


@pytest.mark.parametrize("command", ["staff_counts", "staff_status"])
def test_staff_command_requires_administrator(command):
    fn = _command_node(command)
    assert fn is not None, f"{command} must exist"
    decs = _decorators(fn)
    assert any("default_permissions" in d and "administrator" in d for d in decs), (
        f"{command} must declare default_permissions(administrator=True)"
    )
    assert any("checks.has_permissions" in d and "administrator" in d for d in decs), (
        f"{command} must enforce administrator at runtime"
    )
    assert any("guild_only" in d for d in decs), f"{command} must be guild_only"


@pytest.mark.parametrize("command", ["staff_counts", "staff_status"])
def test_staff_command_reply_is_private(command):
    fn = _command_node(command)
    assert fn is not None
    src = ast.unparse(fn)
    sends = [ln for ln in src.splitlines() if "send_message" in ln or "followup.send" in ln]
    assert sends, f"{command} must send a reply"
    # Every branch that emits staff KPI data must be ephemeral.
    non_ephemeral = [ln.strip() for ln in sends if "ephemeral=True" not in ln]
    assert not non_ephemeral, (
        f"{command} leaks staff data to the channel: {non_ephemeral}"
    )


def test_staff_setup_guard_is_preserved():
    """The reference command must stay locked."""
    fn = _command_node("staff_setup")
    decs = _decorators(fn)
    assert any("checks.has_permissions" in d and "administrator" in d for d in decs)


def test_no_staff_command_is_left_without_a_guard():
    for command in ("staff_counts", "staff_status", "staff_setup"):
        fn = _command_node(command)
        assert fn is not None
        decs = _decorators(fn)
        guarded = any(
            "checks.has_permissions" in d or "checks.is_owner" in d or "guild_only" in d
            for d in decs
        )
        assert guarded, f"{command} has no guard at all"
