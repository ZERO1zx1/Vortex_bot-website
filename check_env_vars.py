"""Check for service role keys or DB URLs in environment."""
import os
results = []
for k, v in sorted(os.environ.items()):
    if any(s in k.lower() for s in ["supabase", "database", "secret", "service_role", "db_url", "postgres"]):
        val = v[:25] + "..." if v else "(empty)"
        results.append(f"{k}: {val}")
if not results:
    results.append("No Supabase/service/secret env vars found (other than those in .env)")
# Also check what keys load_dotenv provides
from dotenv import load_dotenv
load_dotenv()
dotenv_keys = [k for k in os.environ if any(s in k.lower() for s in ["supabase", "token", "secret", "service", "database", "db_"])]
results.append(f"\nAll dotenv-related keys visible to Python: {sorted(dotenv_keys)}")

with open("env_check_result.txt", "w") as f:
    f.write("\n".join(results))
