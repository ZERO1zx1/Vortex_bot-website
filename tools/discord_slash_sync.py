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

Requirements: python-dotenv + requests (install requirements.txt).
Make sure .env in the repo root contains: DISCORD_TOKEN=...
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEBSITE_JS = os.path.join(APP_ROOT, "website", "js", "commands.js") if os.path.exists(
    os.path.join(APP_ROOT, "website")) else None
sys.path.insert(0, os.path.join(APP_ROOT, "website", "tools"))

from catalog_source import command_array_bounds, command_rows

DEFAULT_APP_ID = "1493212321231802408"  # 𝓐𝓮𝓽𝓱𝓮𝓻 蒼穹 bot client id
API = "https://discord.com/api/v10"


# ---------------------------------------------------------------- helpers

def ensure_deps():
    missing = [name for name in ("dotenv", "requests") if importlib.util.find_spec(name) is None]
    if missing:
        raise SystemExit("Missing dependencies: install this repository's requirements.txt first.")


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
    endpoints = [f"{API}/applications/{DEFAULT_APP_ID}/commands"]
    if guild_id:
        endpoints.append(f"{API}/applications/{DEFAULT_APP_ID}/guilds/{guild_id}/commands")
    merged = {}
    for url in endpoints:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        for command in response.json():
            if command.get("type", 1) == 1:
                merged[command["name"]] = command

    def flatten(command, prefix=""):
        name = f"{prefix}{command['name']}"
        children = [option for option in command.get("options", []) if option.get("type") in (1, 2)]
        if children:
            for child in children:
                yield from flatten(child, name + " ")
        else:
            yield {"name": name, "description": command.get("description", "")}

    for command in merged.values():
        out.extend(flatten(command))
    return out


def load_catalog() -> tuple[str, set]:
    """Return (raw commands.js text, set of command names in it)."""
    with open(WEBSITE_JS, encoding="utf-8") as f:
        text = f.read()
    names = {row["name"] for row in command_rows(text) if row.get("example", "").startswith("/")}
    return text, names


def sync_update(raw: str, missing: list[dict]) -> str:
    """Insert missing commands (as JS objects) before the closing of COMMAND_LIST."""
    objects = []
    for c in missing:
        desc = c.get("description") or ""
        row = {"name": c["name"], "cat": "Utility", "desc": desc or "(дэлгэрэнгүйгүй)",
               "type": "slash", "icon": "⚙️", "args": [], "example": f"/{c['name']}",
               "descEN": desc or "(no description)"}
        objects.append("  { " + ", ".join(
            f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in row.items()
        ) + " }")
    block = ",\n".join(objects)
    _, idx = command_array_bounds(raw)
    head = raw[:idx].rstrip()
    separator = "" if head.endswith(("[", ",")) else ","
    return head + separator + "\n" + block + "\n" + raw[idx:]


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description="Compare registered Discord slash commands with the website.")
    parser.add_argument("--guild", help="Include this guild's commands alongside global commands.")
    parser.add_argument("--update", action="store_true", help="Append missing commands to the website catalog.")
    options = parser.parse_args()
    ensure_deps()
    guild = options.guild
    do_update = options.update

    if WEBSITE_JS is None or not os.path.exists(WEBSITE_JS):
        sys.exit("ERROR: website/js/commands.js not found. "
                 "Keep the static website in this repository's website/ directory.")

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
