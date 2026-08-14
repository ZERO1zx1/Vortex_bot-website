"""Verify which required tables exist in live Supabase (non-destructive)."""
import os
import json
from dotenv import load_dotenv, dotenv_values
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")
print(f"SUPABASE_URL set: {bool(url)}")
print(f"SUPABASE_KEY set: {bool(key)}")

if not url or not key:
    print("Cannot connect - missing credentials")
    raise SystemExit(1)

client = create_client(url, key)

REQUIRED_TABLES = [
    "economy", "levels", "giveaways", "temproles",
    "role_income", "tempvoice_setup_msg",
    "game_stats", "shop_stock", "user_inventory",
    "marriages", "warnings", "temp_channels", "guild_config",
    "lottery", "lottery_entries",
]

# Use PostgREST root endpoint to list exposed tables/columns
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Accept": "application/json",
}
import urllib.request
root_url = f"{url}/rest/v1/"
req = urllib.request.Request(root_url, headers=headers)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        schema_info = json.loads(resp.read().decode())
    exposed = set(schema_info.keys())
except Exception as e:
    print(f"Root endpoint failed: {e}")
    schema_info = {}
    exposed = set()

print("\n=== Exposed tables via PostgREST root ===")
for t in sorted(exposed):
    cols = list(schema_info[t].keys()) if isinstance(schema_info.get(t), dict) else []
    print(f"  {t} ({len(cols)} cols)")

print("\n=== Required table check ===")
for t in REQUIRED_TABLES:
    if t in exposed:
        print(f"  [OK] {t}")
    else:
        try:
            r = client.from_(t).select("*", count="exact").limit(0).execute()
            print(f"  [OK] {t} (selectable)")
        except Exception as e:
            print(f"  [MISSING] {t} -> {type(e).__name__}: {str(e)[:200]}")
