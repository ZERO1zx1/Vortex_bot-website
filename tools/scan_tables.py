#!/usr/bin/env python3
"""Scan all Python sources and collect every table name referenced via the
database manager (table= / table( kwargs, raw SQL strings, RPC names).

Used to cross-check migrations against actual bot usage. Read-only.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Table-like string literals that appear as table=... kwargs or in SQL
KNOWN = re.compile(r"^[a-z][a-z0-9_]{2,40}$")

# db API calls whose first/`table` argument is a table name
DB_METHODS = {
    "fetch", "fetch_one", "fetch_all", "fetchone", "fetchall", "fetch_safe",
    "insert", "upsert", "update", "delete", "increment",
    "count", "table", "from_",
    "execute", "execute_sync",
}


def collect_from_file(path: Path, found: dict[str, set[str]]):
    try:
        src = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        # db.method("table") or db.method(table="...")
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Attribute):
                name = func.attr
            if name in DB_METHODS:
                args = list(node.args)
                if args and isinstance(args[0], ast.Constant) and isinstance(args[0].value, str):
                    v = args[0].value
                    if KNOWN.match(v):
                        found.setdefault(v, set()).add(str(path.name))
                for kw in node.keywords:
                    if kw.arg == "table" and isinstance(kw.value, ast.Constant) and isinstance(kw.value, str):
                        v = kw.value.value
                        if KNOWN.match(v):
                            found.setdefault(v, set()).add(str(path.name))
        # f-strings / SQL: FROM <table>, INSERT INTO <table>
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for m in re.finditer(
                r"(?:FROM|INTO|UPDATE|JOIN)\s+([a-z][a-z0-9_]{2,40})", node.value
            ):
                v = m.group(1)
                if KNOWN.match(v) and v not in ("select", "where", "values", "order", "group"):
                    found.setdefault(v, set()).add(str(path.name))


def main() -> int:
    found: dict[str, set[str]] = {}
    for p in BASE.rglob("*.py"):
        if ".git" in p.parts or "__pycache__" in p.parts:
            continue
        collect_from_file(p, found)

    tables = sorted(found)
    print(f"== {len(tables)} table names referenced in code ==")
    for t in tables:
        print(f"  {t:32s} <- {', '.join(sorted(found[t]))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
