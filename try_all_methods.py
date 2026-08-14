"""Try all possible methods to execute SQL on Supabase via the httpx session."""
import os
import json
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("SUPABASE_URL", "")
key = os.getenv("SUPABASE_KEY", "")

import re
proj_match = re.search(r"https://([^.]+)\.supabase\.co", url)
project_ref = proj_match.group(1) if proj_match else "unknown"

results = []

# ── Get the httpx session from supabase client ──
try:
    from supabase import create_client
    client = create_client(url, key)
    sess = client.postgrest.session  # httpx.Client
    lines = [f"Session type: {type(sess)}"]
    lines.append(f"Session headers: {dict(sess.headers)}")
    lines.append(f"Session base_url: {sess.base_url}")

    # Try Management API SQL endpoint via httpx session
    mgmt_url = f"https://api.supabase.com/v1/projects/{project_ref}/database/query"
    payload = {"query": "SELECT 1", "default_schema": "public"}
    lines.append(f"\n--- POST to Management API via httpx session ---")
    try:
        r = sess.post(mgmt_url, json=payload, timeout=15)
        lines.append(f"Status: {r.status_code}")
        lines.append(f"Body: {r.text[:300]}")
    except Exception as e:
        lines.append(f"Failed: {type(e).__name__}: {str(e)[:200]}")

    results.extend(lines)
except Exception as e:
    results.append(f"Client/session setup failed: {type(e).__name__}: {str(e)[:200]}")

# ── Try Edge Functions ──
results.append("\n--- Edge Functions ---")
try:
    # List deployed functions
    r = sess.get(f"{url}/functions/v1/", timeout=15)
    results.append(f"List functions: {r.status_code} {r.text[:300]}")
except Exception as e:
    results.append(f"List functions failed: {type(e).__name__}: {str(e)[:200]}")

# Try common function names
for fn_name in ["sql", "exec", "postgres", "db", "query"]:
    try:
        r = sess.post(f"{url}/functions/v1/{fn_name}", json={"sql": "SELECT 1"}, timeout=10)
        results.append(f"Function '{fn_name}': {r.status_code} {r.text[:200]}")
    except Exception as e:
        results.append(f"Function '{fn_name}': {type(e).__name__}: {str(e)[:150]}")

# ── Try PostgREST with special headers ──
results.append("\n--- PostgREST raw request ---")
try:
    r = sess.post(
        f"{url}/rest/v1/",
        headers={"Prefer": "resolution=merge-duplicates"},
        json={"select": "1"},
        timeout=15,
    )
    results.append(f"PostgREST POST: {r.status_code} {r.text[:300]}")
except Exception as e:
    results.append(f"PostgREST POST failed: {type(e).__name__}: {str(e)[:200]}")

# ── Try using rpc with a creative function name ──
results.append("\n--- RPC attempts ---")
for fn_name in ["create_table", "make_table", "sql_exec", "exec_sql", "setup_table"]:
    try:
        r = client.rpc(fn_name, {"query": "CREATE TABLE IF NOT EXISTS test_temp(id int)"}).execute()
        results.append(f"RPC '{fn_name}': {r}")
    except Exception as e:
        err = str(e)
        results.append(f"RPC '{fn_name}': {err[:200]}")

with open("all_methods_output.txt", "w") as f:
    f.write("\n".join(str(r) for r in results))
