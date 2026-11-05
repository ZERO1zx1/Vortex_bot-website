"""S18  Item-consumption sites must honour remove_item()'s refusal.

`remove_item` is lock-protected and returns False when the stock check fails.
Every caller that ignored that return value applied its effect anyway, so two
simultaneous invocations could both pass the earlier `inventory` read while
only one item was actually consumed -- a free item and a free effect.

The marriage case was worse than a free effect: `add_marriage` ran *before*
the ring was removed, so a refused removal reported an error while the
marriage row already existed.
"""

import ast
import pathlib

SITES = {
    "src/cogs/shop/shop.py": [
        "await self.remove_item(ctx.author.id, guild_id, item_id, 1)",
        'await self.remove_item(ctx.author.id, guild_id, item["id"], 1)',
    ],
    "src/cogs/shop/carts.py": [
        "await shop.remove_item(self.member.id, interaction.guild.id, item_id, 1)",
    ],
    "src/cogs/shop/cafe.py": [
        "await shop.remove_item(ctx.author.id, ctx.guild.id, food_id, 1)",
    ],
    "src/cogs/community/marriage.py": [
        "await shop.remove_item(",
    ],
}


def _lines(rel: str) -> list[str]:
    return pathlib.Path(rel).read_bytes().decode("utf-8-sig").split("\n")


def _find(rel: str, needle: str) -> int:
    for i, line in enumerate(_lines(rel)):
        if needle in line and not line.strip().startswith("#"):
            return i
    raise AssertionError(f"{rel}: {needle!r} not found")


def test_every_consumption_site_checks_the_result():
    for rel, needles in SITES.items():
        lines = _lines(rel)
        for needle in needles:
            idx = _find(rel, needle)
            window = "\n".join(lines[max(0, idx - 5): idx + 4])
            assert "not await" in window, (
                f"{rel}:{idx + 1} discards remove_item()'s refusal -> free item\n{window}"
            )


def test_marriage_consumes_the_ring_before_writing_the_marriage():
    rel = "src/cogs/community/marriage.py"
    ring = _find(rel, "await shop.remove_item(")
    marriage = _find(rel, "await self.cog.add_marriage(")
    assert ring < marriage, (
        "the ring must be consumed first; otherwise a refused removal leaves a "
        "marriage that was already persisted"
    )


def test_marriage_guard_returns_before_add_marriage():
    src = "\n".join(_lines("src/cogs/community/marriage.py"))
    tree = ast.parse(src)
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        for fn in cls.body:
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = ast.unparse(fn)
            if "add_marriage(" not in body:
                continue
            guard = body.index("remove_item(")
            assert "return" in body[guard:body.index("add_marriage(")], (
                "the refusal path must return before the marriage is written"
            )
            return
    raise AssertionError("no marriage-writing function found")


def test_shop_sites_report_a_refusal_to_the_user():
    """A refusal must be visible, not silently swallowed."""
    src = "\n".join(_lines("src/cogs/shop/shop.py"))
    assert src.count("БАРААГ ХАСАХ БОЛСОНГҮЙ") >= 4, (
        "each guarded shop site must tell the user the item could not be taken"
    )


def test_no_guarded_site_uses_a_bare_await_for_consumption():
    """Guard against a future site reintroducing the bug."""
    for rel, needles in SITES.items():
        for needle in needles:
            idx = _find(rel, needle)
            line = _lines(rel)[idx]
            assert "not await" in line, (
                f"{rel}:{idx + 1} must negate the remove_item() result, not await it bare"
            )
