#!/usr/bin/env python3
"""
Supabase migration баталгаажуулах скрипт
========================================
Таны PC дээр `database/migrations/000_complete_schema.sql` migration
Supabase project-д амжилттай ажилласан эсэхийг шалгана.

Хэрэглээ (PowerShell):
    py -3.12 check_migration_applied.py

Хэрвээ `.env` файл байхгүй бол шууд:
    py -3.12 check_migration_applied.py --url "https://onpxpvemmjesobxpilgd.supabase.co" --key "ваш_anon_эсвэл_service_role_ключ"

Энэ скрипт зөвхөн УНШДАГ (read-only). Database-д ямар ч өөрчлөлт оруулахгүй.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error
import urllib.parse

EXPECTED_TABLES = [
    "economy", "levels", "giveaways", "temproles", "role_income",
    "tempvoice_setup_msg", "user_inventory", "staff_config", "staff_members",
    "staff_activity", "leveling_config", "shop_stock",
]

# Бүрэн schema-д байх ёстой бүх хүснэгтүүд (000_complete_schema.sql-аас).
# Энэ жагсаалтыг ботын кодын бодит хэрэглээнээс (tools/scan_tables.py) гаргасан:
# db_manager-ийн бүх insert/update/upsert/delete/fetch дуудлага + TABLE тогтмолууд
# (automod_config, reaction_roles) + website heartbeat (bot_status).
ALL_TABLES = [
    "adoptions", "automod_config", "avatar_log_config", "bot_status",
    "confession_blacklist", "confession_config", "confession_cooldown",
    "confession_messages", "counting_config", "counting_progress",
    "counting_stats", "custom_replies", "daily_stats", "economy",
    "economy_cooldowns_config", "economy_fail_rates", "economy_fines_config",
    "economy_payouts_config", "game_stats", "giveaway_entries", "giveaways",
    "greeting_config", "greeting_templates", "guild_config", "invite_joins",
    "invite_labels", "invite_log_config", "invite_stats", "level_rewards",
    "level_roles", "leveling_config", "leveling_exceptions", "levels",
    "marketplace_listings", "marriage_gifts", "marriage_guild_config",
    "marriage_proposals", "marriage_user_settings", "marriages",
    "pvp_cooldowns", "quest_history", "reaction_roles", "role_income",
    "shop_stock", "staff_activity", "staff_config", "staff_members",
    "staff_weekly_winners", "sticky_messages", "temp_channels",
    "temprole_config", "temproles", "tempvoice_setup_msg", "user_drunk",
    "user_inventory", "user_quests", "warnings", "work_phrases",
]

# Хүснэгтийн дэлгэрэнгүй мэдээллийг PostgREST-ээр шалгах
# `limit=0` зөвхөн хүснэгт байгаа эсэхийг шалгадаг, мөр буцаахгүй.


def check_table(base_url: str, key: str, table: str) -> tuple[bool, str]:
    """Хүснэгт байгаа эсэхийг REST API-ээр шалгах. Returns (exists, message)."""
    url = f"{base_url.rstrip('/')}/rest/v1/{urllib.parse.quote(table)}?limit=0&select=*"
    req = urllib.request.Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, f"OK (HTTP {resp.status})"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except Exception:
            pass
        if e.code == 404:
            return False, f"ХҮСНЭГТ БАЙХГҮЙ (PGRST205 — migration ажиллуулаагүй эсвэл алдаатай ажилласан)"
        if e.code == 401 or e.code == 403:
            return False, (f"Холбогдох эрхгүй (HTTP {e.code}) — хүснэгт дээр \"anon\" рольд SELECT "
                           f"GRANT байхгүй, эсвэл Row Level Security (RLS) асалсан ч access policy "
                           f"байхгүй. database/migrations/000_complete_schema.sql-ийн сүүлийн хэсэгт "
                           f"байгаа 'DISABLE ROW LEVEL SECURITY' болон 'GRANT ALL ... TO anon' "
                           f"тогтоолтуудыг SQL Editor дээр ажиллуул.")
        return False, f"HTTP {e.code}: {body[:160]}"
    except urllib.error.URLError as e:
        return False, f"Холбогдох боломжгүй: {e.reason}"
    except Exception as e:
        return False, f"Тодорхойгүй алдаа: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Supabase migration баталгаажуулах (read-only)")
    parser.add_argument("--url", help="Supabase project URL (https://<id>.supabase.co)")
    parser.add_argument("--key", help="anon эсвэл service_role түлхүүр")
    args = parser.parse_args()

    # Түлхүүр/URL-ийг ашиглах: CLI > .env > supabase .env.example замд байгаа
    url = args.url
    key = args.key
    if not url or not key:
        try:
            from dotenv import load_dotenv
            import os
            load_dotenv(".env", override=False)
            url = url or os.getenv("SUPABASE_URL")
            key = key or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
        except ImportError:
            pass
    if not url or not key:
        print("Алдаа: SUPABASE_URL ба SUPABASE_KEY/SUPABASE_SERVICE_ROLE_KEY олдсонгүй.")
        print("Хэрэглэх: py -3.12 check_migration_applied.py --url '...' --key '...'")
        return 2

    print(f"Supabase: {url}")
    print("=" * 60)

    # 1) Bot-ын шаарддаг гол 12 хүснэгт
    print("\n[1] Bot-ын шаарддаг гол хүснэгтүүд:")
    missing = []
    for table in EXPECTED_TABLES:
        ok, msg = check_table(url, key, table)
        mark = "OK " if ok else "X  "
        print(f"  {mark} {table:24s} {msg}")
        if not ok:
            missing.append(table)

    # 2) Бүрэн schema-ийн хүснэгтүүд
    print(f"\n[2] Бүрэн schema-ийн {len(ALL_TABLES)} хүснэгт шалгах:")
    missing_all = []
    for table in ALL_TABLES:
        ok, msg = check_table(url, key, table)
        mark = "OK " if ok else "X  "
        print(f"  {mark} {table:24s} {msg}")
        if not ok:
            missing_all.append(table)

    # Дүгнэлт
    print("=" * 60)
    if not missing_all:
        print(f"ҮР ДҮН: Бүх {len(ALL_TABLES)} хүснэгт Supabase дээр байна.")
        print("Migration амжилттай ажилласан байна. Bot-оо restart хийж болно.")
        return 0
    if missing:
        print(f"\nҮР ДҮН: {len(missing_all)} хүснэгт байхгүй байна.")
        print("Шаардлагатай 12 хүснэгтийн {0} нь дутуу байна.".format(len(missing)))
        print("-> Supabase Dashboard > SQL Editor > New query дээр")
        print("   database/migrations/000_complete_schema.sql бүх агуулгыг paste хийж Run хийнэ үү.")
        print("   (Энэ файл нь хүснэгтүүдийг үүсгээд RLS-ийг унтрааж, \"anon\" рольд")
        print("    бүрэн эрх GRANT хийдэг — бүгдийг нэг удаа ажиллуулна.)")
        return 1
    print(f"\nҮР ДҮН: {len(missing_all)} хүснэгт байхгүй байна (гол 12 хүснэгт бүгд байна).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
