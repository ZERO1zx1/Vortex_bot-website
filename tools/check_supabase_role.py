"""Diagnose the Supabase role of every configured key.

The bot must connect with role=service_role. If the env value of
SUPABASE_SERVICE_ROLE_KEY / SUPABASE_SECRET_KEY / SUPABASE_KEY is actually
an anon/publishable JWT, every table access fails with 42501
("GRANT ... TO anon" hint).

Usage:
    python tools/check_supabase_role.py

Prints the JWT role claim for each configured variable without revealing
the full key. New-style keys (sb_secret_, sb_publishable_) are not JWTs
and are identified by prefix; a new-style secret is a server key.

Exit code: 0 when a server-level key is configured, 1 otherwise.
"""
import base64
import binascii
import json
import os
import sys
from pathlib import Path

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SERVER_ROLES = ("service_role", "postgres", "supabase_admin", "authenticator")
PUBLIC_ROLES = ("anon", "authenticated")
SERVER_KEY_ENVS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_KEY",
)

_URL_HEAD = "https://zwpgweaikpjkftkzmlak.supabase.co"


def decode_payload(token: str):
    """Decode a JWT payload (no signature verification) or None."""
    if not token or "." not in token:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return decoded if isinstance(decoded, dict) else None
    except (binascii.Error, ValueError, UnicodeDecodeError, IndexError):
        return None


def role_of(key: str) -> str:
    """Return 'service_role', 'anon', 'authenticated', 'secret(new)' or 'unknown'."""
    if not key:
        return "(not set)"
    if key.startswith("sb_publishable_"):
        return "anon (new sb_publishable_)"
    if key.startswith("sb_secret_"):
        return "service_role (new sb_secret_)"
    payload = decode_payload(key)
    if payload is None:
        return "unknown (not a JWT)"
    role = payload.get("role", "unknown")
    return f"{role} (JWT)"


def masked(key: str) -> str:
    if not key or len(key) < 32:
        return "(empty or too short)"
    return f"(configured; {len(key)} characters; redacted)"


def main() -> int:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
    print("=== Supabase URL ===")
    url = os.getenv("SUPABASE_URL", "") or "(not set)"
    print(f"  SUPABASE_URL            = {url}")
    if url and url != _URL_HEAD:
        print(f"  (project host differs from repo default '{_URL_HEAD}')")

    print("\n=== Server keys (in precedence order) ===")
    found_server = False
    for env in SERVER_KEY_ENVS:
        key = os.getenv(env, "").strip()
        role = role_of(key)
        payload = decode_payload(key)
        is_server = key.startswith("sb_secret_") or (
            payload is not None and payload.get("role") in SERVER_ROLES
        )
        if is_server and key:
            found_server = True
        print(f"  {env:29}= {role:32} {masked(key)}")

    anon = os.getenv("SUPABASE_ANON_KEY", "")
    print("\n=== Publishable / anon (for the website only) ===")
    print(f"  SUPABASE_ANON_KEY       = {role_of(anon):32} {masked(anon)}")

    if not found_server:
        print("\n❌ No server-level (service_role / sb_secret_) key is configured.")
        print("   Configure a server-level key before starting the bot.")
        return 1
    print("\n✅ A server-level key is configured in precedence order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
