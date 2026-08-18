#!/usr/bin/env python3
"""Sync command catalog i18n from js/commands.js into js/app.js AETHER_I18N.

Reads every command's `desc` (MN) and `descEN` (EN) and ensures
`cmd.<name>.desc` exists in both language dictionaries of AETHER_I18N.
Missing keys are inserted in sorted order right after the last existing
`cmd.*.desc` entry (or before `'invite.title1'`).

Also emits `cmd.<name>.name` (command title, e.g. "A!daily") in both dicts,
so cards can render bilingual titles consistently.

Usage: python3 tools/sync_cmd_i18n.py
"""
import re
import sys

BASE = '/home/ubuntu/Vortex/website'

def read_cmds():
    src = open(f'{BASE}/js/commands.js').read()
    start = src.find('COMMANDS = [')
    if start == -1:
        raise SystemExit('COMMANDS array not found')
    end = src.find('];', start)
    blob = src[start:end]
    cmds = []
    for m in re.finditer(r"\{ name: '([^']+)',\s*cat: '[^']+',\s*icon: '[^']+',\s*desc: '([^']*)',\s*descEN:\"([^\"]*)\"", blob):
        cmds.append({'name': m.group(1), 'mn': m.group(2), 'en': m.group(3)})
    # Fallback for args/example order variations
    if not cmds:
        for m in re.finditer(r"name: '([^']+)'.*?desc: '([^']*)'.*?descEN:\"([^\"]*)\"", blob, re.S):
            cmds.append({'name': m.group(1), 'mn': m.group(2), 'en': m.group(3)})
    return cmds

def sync(app_src, cmds, lang):
    """Insert missing cmd.{name}.desc entries for one language block."""
    # Locate the lang block
    pat = re.compile(rf"^  {lang}: \{{", re.M)
    m = pat.search(app_src)
    if not m:
        raise SystemExit(f'{lang} block not found')
    block_start = m.end()
    depth = 0
    block_end = block_start
    for k in range(block_start, len(app_src)):
        if app_src[k] == '{':
            depth += 1
        elif app_src[k] == '}':
            depth -= 1
            if depth == 0:
                block_end = k
                break
    block = app_src[block_start:block_end]

    # existing keys in block
    existing = set(re.findall(r"^    '([^']+)':", block, re.M))

    new_lines = []
    for c in sorted(cmds, key=lambda x: x['name']):
        key = f"cmd.{c['name']}.desc"
        if key in existing:
            continue
        val = c['mn'] if lang == 'mn' else c['en']
        val = val.replace('\\', '\\\\').replace("'", "\\'")
        new_lines.append(f"    '{key}': '{val}',")

    if not new_lines:
        return app_src, 0

    # Find insertion anchor: last cmd.*.desc line in block
    anchor = None
    for lm in re.finditer(r"^    'cmd\.[a-z0-9_]+\.desc': '[^']*',?$", block, re.M):
        anchor = block_start + lm.end()
    if anchor is None:
        # before 'invite.title1' entry
        im = re.search(r"^    'invite\.title1':", block, re.M)
        if im:
            anchor = block_start + im.start() - 1  # newline before
            new_insert = '\n' + '\n'.join(new_lines)
        else:
            return app_src, 0
    else:
        new_insert = '\n' + '\n'.join(new_lines)
        # anchor is already right after the last desc line; insert after the newline that follows
    return app_src[:anchor] + new_insert + app_src[anchor:], len(new_lines)

def main():
    cmds = read_cmds()
    print(f'read {len(cmds)} commands from commands.js')
    app = f'{BASE}/js/app.js'
    src = open(app).read()
    n_en = n_mn = 0
    src, n_en = sync(src, cmds, 'en')
    src, n_mn = sync(src, cmds, 'mn')
    open(app, 'w').write(src)
    print(f'inserted {n_en} EN + {n_mn} MN cmd desc entries')

if __name__ == '__main__':
    main()
