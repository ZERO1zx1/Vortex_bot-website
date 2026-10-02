#!/usr/bin/env python3
"""
Supabase migration баталгаажуулах скрипт
========================================
`src/database/migrations/000_aether_complete.sql` bootstrap-ийн хүснэгтүүд
Supabase project-д байгаа, унших эрхтэй эсэхийг шалгана. RPC function-ууд болон
incremental migration-уудын бүрэн төлөвийг зөвхөн хүснэгтээр батлахгүй.

Хэрэглээ (PowerShell):
    py -3.12 tools/check_migration_applied.py

Хэрвээ `.env` файл байхгүй бол шууд:
    py -3.12 tools/check_migration_applied.py --url "https://<id>.supabase.co" --key "<service_role_эсвэл_anon_ключ>"

Энэ скрипт зөвхөн УНШДАГ (read-only). Database-д ямар ч өөрчлөлт оруулахгүй.

Гарцын бүртгэлтэй 4 төлөв:
  OK               Хүснэгт байна, уншиж болно
  MISSING          Хүснэгт байхгүй (PGRST205 / HTTP 404)         -> migration ажиллуулах
  PERMISSION       service_role/тухайн рольд GRANT байхгүй (42501) -> bootstrap GRANT-уудыг шалгах
  UNAVAILABLE      Холболт/servertail алдаа (5xx/network)          -> дахин оролдох
"""
from __future__ import annotations

import argparse
import logging
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
logger = logging.getLogger(__name__)
REPO = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = [
    "economy", "levels", "giveaways", "temproles", "role_income",
    "tempvoice_setup_msg", "user_inventory", "staff_config", "staff_members",
    "staff_activity", "leveling_config", "shop_stock", "ticket_config", "tickets",
    "automation_rules", "automation_runs", "anime_clash_profiles",
    "poker_pending_payouts", "economy_balance_references",
]

# Бүрэн schema-д байх ёстой бүх хүснэгтүүд (000_aether_complete.sql-аас).
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
    "user_inventory", "user_quests", "warnings", "work_phrases", "ticket_config",
    "tickets", "automation_rules", "automation_runs", "anime_clash_profiles",
    "poker_pending_payouts", "economy_balance_references",
]

# Хүснэгтийн дэлгэрэнгүй мэдээллийг PostgREST-ээр шалгах
# `limit=0` зөвхөн хүснэгт байгаа эсэхийг шалгадаг, мөр буцаахгүй.


def check_table(base_url: str, key: str, table: str) -> tuple[str, str]:
    """Хүснэгт байгаа эсэхийг REST API-ээр шалгах.

    Returns (status, message) where status is one of:
      "OK", "MISSING", "PERMISSION", "UNAVAILABLE", "ERROR"
    """
    url = f"{base_url.rstrip('/')}/rest/v1/{urllib.parse.quote(table)}?limit=0&select=*"
    req = urllib.request.Request(url, headers={
        "apikey": key,
        "Authorization": f"Bearer {key}",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return "OK", f"OK (HTTP {resp.status})"
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")
        except OSError:
            logger.warning("Could not read migration-check HTTP error response", exc_info=True)
        if e.code >= 500:
            return "UNAVAILABLE", f"Supabase service unavailable (HTTP {e.code}): {body[:160]}"
        if e.code == 404 or "PGRST205" in body:
            return "MISSING", (
                "ХҮСНЭГТ БАЙХГҮЙ (PGRST205 / HTTP 404) — "
                "src/database/migrations/000_aether_complete.sql bootstrap-ийг шалга"
            )
        if e.code in (401, 403):
            if "42501" in body or "permission denied" in body.lower():
                return "PERMISSION", (
                    "ЭРХ БАЙХГҮЙ (42501 permission denied) — тухайн рольд (энэ key) SELECT "
                    "GRANT алга. src/database/migrations/000_aether_complete.sql дахь GRANT-уудыг шалга."
                )
            return "PERMISSION", (
                f"Холбогдох эрхгүй (HTTP {e.code}) — ашиглаж буй key нь anon бол RLS/GRANT "
                f"улмаас хүснэгт харагдахгүй байна. --key-ээр service_role түлхүүр дамжуул."
            )
        return "ERROR", f"HTTP {e.code}: {body[:160]}"
    except urllib.error.URLError as e:
        return "UNAVAILABLE", f"Холбогдох боломжгүй: {e.reason}"
    except (TimeoutError, ConnectionError) as e:
        return "UNAVAILABLE", f"Холболтын алдаа: {e}"
    except Exception as e:
        logger.exception("Unexpected migration-check failure for table %s", table)
        return "ERROR", f"Тодорхойгүй алдаа: {e}"


def migration_is_complete(counts: dict[str, int], total: int) -> bool:
    """Only a fully observed OK result may authorize restart/deploy."""
    return (
        counts.get("OK", 0) == total
        and all(counts.get(key, 0) == 0 for key in (
            "MISSING", "PERMISSION", "UNAVAILABLE", "ERROR"
        ))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Supabase migration баталгаажуулах (read-only)")
    parser.add_argument("--url", help="Supabase project URL (https://<id>.supabase.co)")
    parser.add_argument("--key", help="anon эсвэл service_role түлхүүр")
    args = parser.parse_args()

    # Түлхүүр/URL-ийг ашиглах: CLI > environment > repository .env
    url = args.url
    key = args.key
    if not url or not key:
        try:
            import os

            from dotenv import load_dotenv

            from src.core.config import pick_server_supabase_key
            load_dotenv(REPO / ".env", override=False)
            url = url or os.getenv("SUPABASE_URL")
            key = key or pick_server_supabase_key()
        except ImportError:
            pass
    if not url or not key:
        print("Алдаа: SUPABASE_URL ба server Supabase key олдсонгүй.")
        print("Хэрэглэх: py -3.12 tools/check_migration_applied.py --url '...' --key '...'")
        return 2

    print(f"Supabase: {url}")
    print("=" * 60)

    def _report(tables: list[str]) -> dict[str, int]:
        counts = {"OK": 0, "MISSING": 0, "PERMISSION": 0, "UNAVAILABLE": 0, "ERROR": 0}
        for table in tables:
            status, msg = check_table(url, key, table)
            counts[status] = counts.get(status, 0) + 1
            mark = {"OK": "OK ", "MISSING": "X  "}.get(status, "!  ")
            print(f"  {mark} {table:24s} {msg}")
        return counts

    # 1) Bot-ын шаарддаг гол хүснэгтүүд
    print("\n[1] Bot-ын шаарддаг гол хүснэгтүүд:")
    counts_exp = _report(EXPECTED_TABLES)
    print("Гол хүснэгтийн үр дүн: " + ", ".join(f"{status}={count}" for status, count in counts_exp.items()))

    # 2) Бүрэн schema-ийн хүснэгтүүд
    print(f"\n[2] Бүрэн schema-ийн {len(ALL_TABLES)} хүснэгт шалгах:")
    counts_all = _report(ALL_TABLES)

    # Дүгнэлт — машинд уншигдах нэг мөр + зөвлөмж
    print("=" * 60)
    summary = "ҮР ДҮН: " + ", ".join(
        f"{k}={v}" for k, v in (("OK", counts_all["OK"]), ("MISSING", counts_all["MISSING"]),
                                ("PERMISSION", counts_all["PERMISSION"]), ("UNAVAILABLE", counts_all["UNAVAILABLE"]),
                                ("ERROR", counts_all["ERROR"]))
    )
    print(summary)
    if migration_is_complete(counts_all, len(ALL_TABLES)):
        print("Бүх шалгасан хүснэгт байна, унших эрхтэй. RPC болон incremental migration-уудыг тусад нь баталгаажуул.")
        return 0
    if counts_all["MISSING"]:
        print("-> Хүснэгтүүд дутуу: 'src/database/migrations/000_aether_complete.sql' bootstrap-ийг шалга.")
    if counts_all["PERMISSION"]:
        print("-> GRANT алдсан: bootstrap-ийн GRANT болон server key тохиргоог шалга.")
    if counts_all["UNAVAILABLE"]:
        print("-> Зарим хүснэгт холболтын алдаагаар шалгагдаагүй; дахин ажиллуул.")
    if counts_all["ERROR"]:
        print("-> Зарим хүснэгт тодорхойгүй API алдаагаар шалгагдаагүй; дээрх HTTP алдааг зас.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
