"""One-off script: verify live Supabase schema and apply missing non-destructive tables."""
import os
import re
import sys
import urllib.request
import json

from dotenv import load_dotenv
load_dotenv()

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

if not url or not key:
    print("FATAL: SUPABASE_URL / SUPABASE_KEY not set in environment")
    sys.exit(1)

proj_match = re.match(r"https://([^.]+)\.supabase\.co", url)
project_ref = proj_match.group(1) if proj_match else "unknown"
print(f"Project ref: {project_ref}")

# ── Method 1: Try PostgREST root to list tables ──
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
}
root_url = f"{url}/rest/v1/"
tables_via_root = []
try:
    req = urllib.request.Request(root_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        schema_info = json.loads(resp.read().decode())
    tables_via_root = sorted(schema_info.keys())
    print(f"\nPostgREST root exposed {len(tables_via_root)} tables:")
    for t in tables_via_root:
        print(f"  - {t}")
except Exception as e:
    print(f"\nPostgREST root failed: {e}")

# ── Method 2: Try psycopg2 direct connection ──
print("\n--- psycopg2 direct connection ---")
try:
    import psycopg2
    host = f"db.{project_ref}.supabase.co"
    conn = psycopg2.connect(
        host=host,
        port=5432,
        dbname="postgres",
        user="postgres",
        password=key,
        connect_timeout=10,
    )
    cur = conn.cursor()
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
    live_tables = set(r[0] for r in cur.fetchall())
    print(f"Connected! Live tables ({len(live_tables)}): {sorted(live_tables)}")

    # ── Apply migration ──
    MIGRATION_SQL = open("database/migrations/20260813_runtime_missing_tables.sql").read()
    print("\nApplying migration SQL (CREATE TABLE IF NOT EXISTS + indexes)...")
    cur.execute(MIGRATION_SQL)
    conn.commit()

    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename;")
    new_tables = set(r[0] for r in cur.fetchall())
    after = sorted(new_tables)
    print(f"\nAfter migration ({len(after)} tables): {after}")

    missing_after = [t for t in ["giveaways","temproles","role_income","tempvoice_setup_msg"] if t not in new_tables]
    if missing_after:
        print(f"STILL MISSING after migration: {missing_after}")
    else:
        print("All required tables present after migration!")

    cur.close()
    conn.close()
except ImportError:
    print("psycopg2 not available")
except Exception as e:
    print(f"psycopg2 failed: {type(e).__name__}: {str(e)[:300]}")
