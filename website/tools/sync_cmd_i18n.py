#!/usr/bin/env python3
"""Sync command catalog i18n from js/commands.js into js/app.js AETHER_I18N.

Reads every command's `desc` (MN) and `descEN` (EN) and ensures
`cmd.<name>.desc` exists in both language dictionaries of AETHER_I18N.
Missing keys are inserted in sorted order right after the last existing
`cmd.*.desc` entry (or before `'invite.title1'`).

Also emits `cmd.<name>.name` (command title, e.g. "A!daily") in both dicts,
so cards can render bilingual titles consistently.

Usage: python website/tools/sync_cmd_i18n.py [--check]
"""
import argparse
import ast
import json
import os
import re
from pathlib import Path

from catalog_source import JS_STRING, closing_delimiter, command_rows

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read_cmds():
    src = Path(BASE, 'js', 'commands.js').read_text(encoding='utf-8')
    return [
        {'name': row['name'], 'mn': row.get('desc', ''), 'en': row.get('descEN', ''),
         'title': f"{'/' if row.get('example', '').startswith('/') else 'A!'}{row['name']}"}
        for row in command_rows(src)
    ]

def sync(app_src, cmds, lang):
    """Insert missing cmd.{name}.desc entries for one language block."""
    # Locate the lang block
    pat = re.compile(rf"^  {lang}: \{{", re.MULTILINE)
    m = pat.search(app_src)
    if not m:
        raise SystemExit(f'{lang} block not found')
    block_start = m.end()
    block_end = closing_delimiter(app_src, m.end() - 1)
    block = app_src[block_start:block_end]

    # existing keys in block
    existing = {
        ast.literal_eval(match.group(1))
        for match in re.finditer(rf"^    ({JS_STRING}):", block, re.MULTILINE)
    }

    new_lines = []
    for c in sorted(cmds, key=lambda x: x['name']):
        for suffix, value in (('desc', c[lang]), ('name', c['title'])):
            key = f"cmd.{c['name']}.{suffix}"
            if key not in existing:
                new_lines.append(f"    {json.dumps(key, ensure_ascii=False)}: {json.dumps(value, ensure_ascii=False)},")
                existing.add(key)

    if not new_lines:
        return app_src, 0

    # Find insertion anchor: last cmd.*.desc line in block
    anchor = None
    for lm in re.finditer(rf"^    ({JS_STRING}):\s*{JS_STRING},?$", block, re.MULTILINE):
        if ast.literal_eval(lm.group(1)).startswith('cmd.'):
            anchor = block_start + lm.end()
    if anchor is None:
        # before 'invite.title1' entry
        im = re.search(r"^    'invite\.title1':", block, re.MULTILINE)
        if im:
            anchor = block_start + im.start() - 1  # newline before
            new_insert = '\n' + '\n'.join(new_lines)
        else:
            raise SystemExit(f'{lang} block has no safe translation insertion anchor')
    else:
        new_insert = '\n' + '\n'.join(new_lines)
        # anchor is already right after the last desc line; insert after the newline that follows
    return app_src[:anchor] + new_insert + app_src[anchor:], len(new_lines)

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Sync website command translations.')
    parser.add_argument('--check', action='store_true', help='Report missing keys without writing files.')
    options = parser.parse_args(argv)
    cmds = read_cmds()
    print(f'read {len(cmds)} commands from commands.js')
    app = f'{BASE}/js/app.js'
    src = Path(app).read_text(encoding='utf-8')
    n_en = n_mn = 0
    src, n_en = sync(src, cmds, 'en')
    src, n_mn = sync(src, cmds, 'mn')
    if options.check:
        print(f'missing {n_en} EN + {n_mn} MN command entries; no files written')
        return int(n_en + n_mn > 0)
    Path(app).write_text(src, encoding='utf-8')
    print(f'inserted {n_en} EN + {n_mn} MN cmd desc entries')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
