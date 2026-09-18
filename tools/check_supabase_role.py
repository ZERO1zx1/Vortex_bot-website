# -*- coding: utf-8 -*-
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
import json
import os
import sys

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SERVER_ROLES = ("service_role", "postgres", "supabase_admin")
PUBLIC_ROLES = ("anon", "authenticated")
SERVER_KEY_ENVS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_KEY",
)

_URL_HEAD = "https://onpxpvemmjesobxpilgd.supabase.co"


def decode_payload(token: str):
    """Decode a JWT payload (no signature verification) or None."""
    if not token or "." not in token:
        return None
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
    except Exception:
        return None


def role_of(key: str) -> str:
    """Return 'service_role', 'anon', 'authenticated', 'secret(new)' or 'unknown'."""
    if not key:
        return "(not set)"
    if key.startswith("sb_publishable_"):
        return "anon (new sb_publishable_)"
    if key.startswith("sb_secret_") or key.startswith("service_role."):
        return "service_role (new sb_secret_)"
    payload = decode_payload(key)
    if payload is None:
        return "unknown (not a JWT)"
    role = payload.get("role", "unknown")
    return f"{role} (JWT)"


def masked(key: str) -> str:
    if not key or len(key) < 32:
        return "(empty or too short)"
    return f"{key[:24]}...{key[-8:]}"


def main() -> int:
    print("=== Supabase URL ===")
    url = SUPABASE_URL or "(not set)"
    print(f"  SUPABASE_URL            = {url}")
    if url and url != _URL_HEAD:
        print(f"  (project host differs from repo default '{_URL_HEAD}')")

    print("\n=== Server keys (in precedence order) ===")
    found_server = False
    for env in SERVER_KEY_ENVS:
        key = os.getenv(env, "").strip()
        role = role_of(key)
        is_server = role.startswith("service_role") or role == "secret (new)"
        if is_server and key:
            found_server = True
        print(f"  {env:29}= {role:32} {masked(key)}")

    anon = os.getenv("SUPABASE_ANON_KEY", "") or os.getenv("SUPABASE_KEY", "")
    print("\n=== Publishable / anon (for the website only) ===")
    print(f"  SUPABASE_ANON_KEY       = {role_of(anon):32} {masked(anon)}")

    if not found_server:
        print("\n❌ No server-level (service_role / sb_secret_) key is configured.")
        print("   The bot will run with anon privileges and every access will 42501.")
        return 1
    print("\n✅ A server-level key is configured in precedence order.")
    return 0


if __name__ == "__main__":
    sys.exit(main())