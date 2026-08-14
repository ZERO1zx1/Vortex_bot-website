"""Test PostgreSQL connection to Supabase via psycopg2."""
import os
import re
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

proj = re.search(r"https://([^.]+)\.supabase\.co", url)
if not proj:
    print(f"FATAL: cannot parse project ref from URL: {url}")
    exit(1)
proj = proj.group(1)
print(f"Project ref: {proj}")

import psycopg2

attempts = [
    (f"{proj}.pooler.supabase.com", 6543, f"postgres.{proj}", "pooler"),
    (f"db.{proj}.supabase.co", 5432, "postgres", "direct"),
    (f"{proj}.supabase.co", 5432, "postgres", "alt-direct"),
]

connected = False
for host, port, user, label in attempts:
    try:
        conn = psycopg2.connect(
            host=host, port=port, dbname="postgres",
            user=user, password=key,
            connect_timeout=8,
        )
        cur = conn.cursor()
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = sorted(r[0] for r in cur.fetchall())
        print(f"\nCONNECTED via {label} ({host}:{port} as {user})!")
        print(f"Live tables ({len(tables)}): {tables}")

        # Read and apply migration
        migration_path = "database/migrations/20260813_runtime_missing_tables.sql"
        if os.path.exists(migration_path):
            with open(migration_path) as f:
                sql = f.read()
            print(f"\nApplying {len(sql)} bytes of migration SQL...")
            cur.execute(sql)
            conn.commit()
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
            new_tables = sorted(r[0] for r in cur.fetchall())
            print(f"After migration ({len(new_tables)} tables): {new_tables}")

            check = ["giveaways","temproles","role_income","tempvoice_setup_msg"]
            missing = [t for t in check if t not in new_tables]
            if missing:
                print(f"STILL MISSING: {missing}")
            else:
                print("All 4 required tables now exist!")
        else:
            print(f"Migration file not found at {migration_path}")

        cur.close()
        conn.close()
        connected = True
        break
    except Exception as e:
        print(f"  {label} ({host}:{port} as {user}): {type(e).__name__}: {str(e)[:200]}")

if not connected:
    print("\nCould not connect via any method. The anon key cannot create tables.")
    print("Will need to use supabase client RPC or a service_role key.")
