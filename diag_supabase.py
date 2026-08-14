"""Diagnostic: check Supabase key type and table existence."""
import os
import json
import urllib.request
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

results = []
results.append(f"SUPABASE_URL set: {bool(url)}")
results.append(f"SUPABASE_URL: {url}")
results.append(f"Key length: {len(key)}")
results.append(f"Key starts with: {key[:20]}...")
results.append(f"Is JWT (eyJ): {key.startswith('eyJ')}")
results.append(f"Is sbp token: {key.startswith('sbp_')}")

# Check table existence via PostgREST root
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
}
root_url = f"{url}/rest/v1/"
try:
    req = urllib.request.Request(root_url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        schema_info = json.loads(resp.read().decode())
    tables = sorted(schema_info.keys())
    results.append(f"\nPostgREST root: {len(tables)} tables exposed")
    for t in tables:
        cols = sorted(schema_info[t].keys()) if isinstance(schema_info[t], dict) else []
        results.append(f"  {t}: {len(cols)} cols")
except Exception as e:
    results.append(f"\nPostgREST root failed: {type(e).__name__}: {str(e)[:200]}")

# Also try the supabase client approach
try:
    from supabase import create_client
    client = create_client(url, key)

    check_tables = [
        "economy", "levels", "giveaways", "temproles",
        "role_income", "tempvoice_setup_msg", "game_stats",
        "shop_stock", "user_inventory", "staff_members",
        "staff_activity", "leveling_config",
    ]

    results.append("\n--- Supabase client table check ---")
    for t in check_tables:
        try:
            r = client.from_(t).select("*", count="exact").limit(0).execute()
            results.append(f"  [OK] {t}")
        except Exception as e:
            err = str(e)
            if "PGRST205" in err or "Could not find" in err:
                results.append(f"  [MISSING] {t}")
            else:
                results.append(f"  [ERROR] {t}: {type(e).__name__}: {err[:150]}")
except Exception as e:
    results.append(f"Supabase client error: {type(e).__name__}: {str(e)[:200]}")

with open("diag_output.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(results))
