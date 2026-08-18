#!/usr/bin/env python3
"""Discord slash commands → website commands.js auto-sync.

What it does:
  1. Fetches ALL registered slash commands (global + guild) from the
     Discord API using your bot token (read from .env → DISCORD_TOKEN).
  2. Compares them against the commands listed in commands.js (website).
  3. Reports commands that exist in Discord but NOT in the website catalog,
     and commands in the website that no longer exist in Discord.
  4. Optionally (--update) appends the missing commands into commands.js
     with sensible placeholders (icon, category, description) so you can
     edit them later.

Usage (Windows):
    py -3.12 tools/discord_slash_sync.py                # report only
    py -3.12 tools/discord_slash_sync.py --update       # patch commands.js
    py -3.12 tools/discord_slash_sync.py --guild GUILD_ID

Requirements: python-dotenv (auto-installs) + requests.
Make sure .env in the repo root contains: DISCORD_TOKEN=...
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE_JS = os.path.join(APP_ROOT, "website", "js", "commands.js") if os.path.exists(
    os.path.join(APP_ROOT, "website")) else None

DEFAULT_APP_ID = "1493212321231802408"  # 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 bot client id
API = "https://discord.com/api/v10"


# ---------------------------------------------------------------- helpers

def ensure_deps():
    try:
        import dotenv  # noqa
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user",
                        "python-dotenv", "requests"], check=True)


def load_token():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(APP_ROOT, ".env"))
    token = os.environ.get("DISCORD_TOKEN", "")
    if not token:
        sys.exit("ERROR: DISCORD_TOKEN not found in .env (repo root).")
    return token


def fetch_commands(token: str, guild_id: str | None):
    import requests
    headers = {"Authorization": f"Bot {token}"}
    out: list[dict] = []
    if guild_id:
        r = requests.get(f"{API}/applications/{DEFAULT_APP_ID}/guilds/{guild_id}/commands",
                         headers=headers, timeout=20)
        r.raise_for_status()
        out = r.json()
    else:
        r = requests.get(f"{API}/applications/{DEFAULT_APP_ID}/commands",
                         headers=headers, timeout=20)
        r.raise_for_status()
        out = r.json()
    # Guild commands do not include global ones; fetch both and merge when no guild
    if not guild_id:
        r2 = requests.get(f"{API}/applications/{DEFAULT_APP_ID}/commands",
                          headers=headers, timeout=20)
        r2.raise_for_status()
        out = r2.json()
    return out


def load_catalog() -> tuple[str, set]:
    """Return (raw commands.js text, set of command names in it)."""
    with open(WEBSITE_JS, encoding="utf-8") as f:
        text = f.read()
    names = set(re.findall(r"name:\s*'([a-zA-Z0-9_]+)'", text))
    return text, names


def sync_update(raw: str, missing: list[dict]) -> str:
    """Insert missing commands (as JS objects) before the closing of COMMAND_LIST."""
    # Find where COMMAND_LIST array items live; append new items at the end
    # right before the last `];` that closes the list.
    objects = []
    for c in missing:
        desc = (c.get("description") or "").replace('"', '\\"').replace("\n", " ")
        objects.append(
            "  {name: '%s', cat: 'other', desc: '%s', type: 'slash', "
            "icon: '⚙️', args: [], example: '/%s', descEN: '%s'}"
            % (c["name"], desc or "(дэлгэрэнгүйгүй)", c["name"], desc or "(no description)")
        )
    block = ",\n".join(objects)
    # Insert before the last line `];` (end of COMMAND_LIST)
    idx = raw.rfind("];")
    return raw[:idx] + ",\n" + block + "\n" + raw[idx:]


# ---------------------------------------------------------------- main

def main():
    ensure_deps()
    import requests  # noqa

    guild = None
    do_update = False
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--guild" and i + 1 < len(args):
            guild = args[i + 1]; i += 2
        elif args[i] == "--update":
            do_update = True; i += 1
        else:
            i += 1

    if WEBSITE_JS is None or not os.path.exists(WEBSITE_JS):
        sys.exit("ERROR: website/js/commands.js not found. "
                 "Run this script from the gurtendev repo root, "
                 "and keep the website repo as a sibling `website/` folder, "
                 "or set WEBSITE_JS path at the top of this file.")

    token = load_token()
    cmds = fetch_commands(token, guild)
    discord_names = {c["name"] for c in cmds}

    if WEBSITE_JS:
        raw, web_names = load_catalog()
    else:
        raw, web_names = "", set()

    only_discord = sorted(discord_names - web_names)
    only_website = sorted(web_names - discord_names)

    print(f"Discord slash commands registered : {len(cmds)}")
    print(f"Commands in website commands.js   : {len(web_names)}")
    print()
    if only_discord:
        print("⚠ NEW in Discord (not in website catalog):")
        for n in only_discord:
            desc = next(c["description"] for c in cmds if c["name"] == n)
            print(f"   + /{n} — {desc[:60]}")
    else:
        print("✅ All Discord slash commands already in the website catalog.")
    if only_website:
        print()
        print("🗑 In website catalog but not registered in Discord:")
        for n in only_website:
            print(f"   - {n}")

    if do_update and only_discord and WEBSITE_JS:
        new_raw = sync_update(raw, [c for c in cmds if c["name"] in only_discord])
        with open(WEBSITE_JS, "w", encoding="utf-8") as f:
            f.write(new_raw)
        print(f"\n✅ Appended {len(only_discord)} commands to website/js/commands.js")
        print("   ⚠ Review the appended entries (cat/icon/args) before committing!")


if __name__ == "__main__":
    main()
