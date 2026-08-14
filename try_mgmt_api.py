"""Try multiple methods to execute SQL on Supabase."""
import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

import re
proj_match = re.search(r"https://([^.]+)\.supabase\.co", url)
project_ref = proj_match.group(1) if proj_match else "unknown"

results = []

# ── Method 1: Supabase Management API ──
results.append("=== Method 1: Management API ===")
mgmt_url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
payload = json.dumps({"query": "SELECT 1 as test", "default_schema": "public"}).encode()
req = urllib.request.Request(
    mgmt_url,
    data=payload,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        results.append(f"SUCCESS: {data}")
except Exception as e:
    results.append(f"FAILED: {type(e).__name__}: {str(e)[:200]}")

# ── Method 2: Supabase Management API with service_role format ──
results.append("\n=== Method 2: Management API (v1, no body schema) ===")
req2 = urllib.request.Request(
    mgmt_url,
    data=payload,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Ctx-Refresh-Token": "true"},
    method="POST",
)
try:
    with urllib.request.urlopen(req2, timeout=15) as resp:
        data = json.loads(resp.read().decode())
        results.append(f"SUCCESS: {data}")
except Exception as e:
    results.append(f"FAILED: {type(e).__name__}: {str(e)[:200]}")

# ── Method 3: Try calling increment RPC (function from schema) ──
results.append("\n=== Method 3: RPC call to 'increment' ===")
try:
    from supabase import create_client
    client = create_client(url, key)
    r = client.rpc("increment", {
        "table_name": "economy",
        "filter_col": "user_id",
        "filter_val": "0",
        "col": "balance",
        "delta": 0,
    }).execute()
    results.append(f"RPC increment call succeeded (function exists + key has RPC access)")
    results.append(f"Response: {r}")
except Exception as e:
    err_str = str(e)
    if "Could not find" in err_str or "PGRST" in err_str:
        results.append(f"RPC function does not exist or table missing: {err_str[:200]}")
    else:
        results.append(f"RPC failed: {type(e).__name__}: {err_str[:200]}")

# ── Method 4: Try PostgREST with Prefer header for raw query ──
results.append("\n=== Method 4: PostgREST raw via httpx ===")
try:
    import httpx
    h = httpx.Client()
    # Try to see if there's an rpc/sql endpoint
    r = h.post(
        f"{url}/rest/v1/rpc/sql_query",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": "SELECT current_database()"},
        timeout=15,
    )
    results.append(f"rpc/sql_query: {r.status_code} {r.text[:200]}")
except Exception as e:
    results.append(f"Failed: {type(e).__name__}: {str(e)[:200]}")

with open("mgmt_output.txt", "w") as f:
    f.write("\n".join(results))
