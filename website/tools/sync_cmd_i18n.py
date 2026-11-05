#!/usr/bin/env python3
"""Audit command copy in the generated catalog.

History
-------
This script used to *copy* every command's `desc`/`descEN` from
`src/data/commands.js` into a parallel set of `cmd.<name>.desc` keys inside
the website's i18n dictionary. That duplication had silently drifted: the two
copies disagreed for 49 commands and 135 commands had no dictionary entry at
all. The dictionary is gone; the catalog is now the single source of truth.

What this script does now
-------------------------
It checks the catalog for the problems that drift actually causes:

  * a command missing `desc` (Mongolian) or `descEN` (English) -> renders blank
    in one language;
  * a command whose `desc`/`descEN` still matches the retired dictionary
    wording recorded in `src/data/divergentDescriptions.js` -> the stale text
    was never reconciled.

The first group is an error and exits non-zero. The second is reported as
reviewable drift and can be opted into via `--strict`.

Usage
-----
  python website/tools/sync_cmd_i18n.py           # audit, exit 1 on problems
  python website/tools/sync_cmd_i18n.py --strict  # also exit 1 on stale drift
"""
import argparse
import json
import os
import re
from pathlib import Path

from catalog_source import command_rows

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = Path(BASE, 'src', 'data', 'commands.js')
DIVERGENT = Path(BASE, 'src', 'data', 'divergentDescriptions.js')

JS_OBJECT = re.compile(r'export const DIVERGENT_(?:EN|MN) = (\{.*?\});', re.DOTALL)


def load_divergent() -> dict:
    """Read the preserved pre-migration wording out of the review file."""
    if not DIVERGENT.is_file():
        return {}
    found = {}
    for match in JS_OBJECT.finditer(DIVERGENT.read_text(encoding='utf-8')):
        found.update(json.loads(match.group(1)))
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Audit command translations in the catalog.')
    parser.add_argument('--strict', action='store_true',
                        help='Also fail when a description still matches retired wording.')
    parser.add_argument('--check', action='store_true',
                        help='Deprecated alias for --strict, kept for old CI calls.')
    options = parser.parse_args(argv)
    strict = options.strict or options.check

    rows = command_rows(CATALOG.read_text(encoding='utf-8'))
    print(f'read {len(rows)} commands from {CATALOG.relative_to(os.path.dirname(BASE))}')

    missing = []
    for row in rows:
        name = row['name']
        gaps = [lang for lang, field in (('MN', 'desc'), ('EN', 'descEN')) if not row.get(field)]
        if gaps:
            missing.append((name, gaps))

    divergent = load_divergent()
    unreconciled = [
        row['name'] for row in rows
        if row['name'] in divergent
        and row.get('descEN') == divergent[row['name']].get('old')
    ]

    for name, gaps in missing:
        print(f'  MISSING {"/".join(gaps)}: {name}')
    print(f'missing descriptions: {len(missing)}')

    if unreconciled:
        print(f'catalog still matches retired dictionary wording: {len(unreconciled)}')
        for name in unreconciled[:20]:
            print(f'  STALE: {name}')
        if len(unreconciled) > 20:
            print(f'  ... and {len(unreconciled) - 20} more')

    if missing:
        return 1
    if strict and unreconciled:
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())