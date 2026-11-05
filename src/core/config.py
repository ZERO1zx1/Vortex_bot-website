import base64
import binascii
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

SRC_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SRC_DIR.parent / ".env")

CONFIG_FILE = SRC_DIR / "config.json"

# ── Supabase key selection ─────────────────────────────────────
# The bot MUST use a server-level (service_role, JWT role or new
# sb_secret_) key, otherwise every table access fails with 42501
# ("GRANT ... TO anon" hint).  ANON/JWT anon keys are publishable keys for
# the website only and must never be selected for the bot.
#
# Precedence:
#   1. SUPABASE_SERVICE_ROLE_KEY  (legacy JWT, role=service_role)
#   2. SUPABASE_SECRET_KEY        (new sb_secret_... key, full server access)
#   3. SUPABASE_KEY               (legacy fallback; only used if JWT is
#                                  actually service_role — never anon)
#
# A candidate is accepted ONLY when its JWT `role` claim is a server role
# (or the key is a new-style sb_secret_ key).  If every configured key is
# anon/publishable the bot logs a hard error at startup instead of silently
# running with anon privileges (root cause of every 42501).
SUPABASE_SERVER_ROLE_ENVS = (
    "SUPABASE_SERVICE_ROLE_KEY",
    "SUPABASE_SECRET_KEY",
    "SUPABASE_KEY",
)
_SERVER_JWT_ROLES = ("service_role", "supabase_admin", "postgres", "authenticator")


def _jwt_payload(key: str) -> dict | None:
    """Decode a JWT payload (no signature check) or None."""
    if not key or "." not in key:
        return None
    try:
        payload = key.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return decoded if isinstance(decoded, dict) else None
    except (binascii.Error, ValueError, UnicodeDecodeError, IndexError):
        return None


def is_server_level_key(key: str) -> bool:
    """True when ``key`` is a server-level Supabase key.

    Accepts new-style ``sb_secret_...`` keys and legacy JWTs whose ``role``
    claim is a server role.  Rejects anon / authenticated / publishable keys.
    """
    if not key:
        return False
    if key.startswith("sb_secret_"):
        return True
    payload = _jwt_payload(key)
    if payload is None:
        return False
    return payload.get("role") in _SERVER_JWT_ROLES


def describe_key(key: str) -> str:
    """Human-readable role of a Supabase key. Never returns the value itself."""
    if not key:
        return "(not set)"
    if key.startswith("sb_publishable_"):
        return "anon (sb_publishable_)"
    if key.startswith("sb_secret_"):
        return "server (sb_secret_)"
    payload = _jwt_payload(key)
    if payload is None:
        return "unrecognised (not a JWT)"
    role = payload.get("role")
    return f"{role} (JWT)" if role else "unrecognised (JWT without role claim)"


def supabase_key_mismatches() -> list[tuple[str, str]]:
    """``(env, actual_role)`` for every server-named variable holding anon.

    ``SUPABASE_SERVICE_ROLE_KEY`` / ``SUPABASE_SECRET_KEY`` / ``SUPABASE_KEY``
    all promise a server-level key.  When one of them actually holds an
    anon/publishable value the bot still behaves correctly -- ``pick_server_-
    supabase_key`` skips it -- but every script that reads the variable
    directly (``os.getenv``) silently receives a publishable key.  This
    returns those mismatches so startup can report them instead of leaving a
    landmine for the next reader of ``.env``.
    """
    return [
        (env, describe_key(os.getenv(env, "").strip()))
        for env in SUPABASE_SERVER_ROLE_ENVS
        if os.getenv(env, "").strip() and not is_server_level_key(os.getenv(env, "").strip())
    ]


_mismatch_reported = False


def report_key_mismatches_once(logger: logging.Logger | None = None) -> list[tuple[str, str]]:
    """Log server-named vars that hold anon keys, once per process.

    Returns the mismatches so callers can assert on them without parsing logs.
    """
    global _mismatch_reported
    if _mismatch_reported:
        return []
    _mismatch_reported = True
    mismatches = supabase_key_mismatches()
    if not mismatches:
        return []
    (logger or logging.getLogger("aether")).error(
        "Supabase env var naming does not match the key it holds (%d mismatch(es)): %s. "
        "These variables are reserved for server-level keys; anon/publishable values are "
        "ignored by the bot, but any tool or script reading them directly gets a "
        "publishable key. Fix: keep the server key in SUPABASE_SECRET_KEY and delete the "
        "misleading entries (or add the publishable key as SUPABASE_ANON_KEY).",
        len(mismatches),
        ", ".join(f"{env}={role}" for env, role in mismatches),
    )
    return mismatches


def pick_server_supabase_key() -> str:
    """First configured key that is server-level; else '' with an ERROR log.

    Supersedes the old "first defined, anon included" fallback which made the
    bot run with anon privileges whenever a publishable key was present.
    """
    logger = logging.getLogger("aether")
    report_key_mismatches_once(logger)
    for env in SUPABASE_SERVER_ROLE_ENVS:
        value = os.getenv(env, "").strip()
        if value and is_server_level_key(value):
            return value
    configured = [env for env in SUPABASE_SERVER_ROLE_ENVS if os.getenv(env, "").strip()]
    if configured:
        logger.error(
            "No server-level Supabase key found. Configured: %s. "
            "Check %s: the value must be a service_role JWT or sb_secret_ key "
            "(Supabase Dashboard -> Settings -> API keys), NOT the anon "
            "publishable key. The bot is currently without DB privileges (42501).",
            ", ".join(configured),
            configured[0],
        )
    return ""


def _parse_int_list(raw: str):
    """Parse a comma-separated string of integers safely."""
    result = []
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result


def load_config():
    """Load config.json, overlaying owner/co-owner IDs from environment variables.

    Environment variables (authoritative when present):
        OWNER_ID   — single Discord user ID
        CO_OWNERS  — comma-separated Discord user IDs
        GUILD_ID   — one or more comma-separated Discord guild IDs used for
                     immediate slash-command sync
    """
    if not os.path.exists(CONFIG_FILE):
        default = {
            "owner_id": None,
            "co_owner_ids": [],
            "prefix": "A!, a!",
            "xp_per_message": 15,
            "voice_xp_per_minute": 1,
            "base_xp_needed": 100,
            "bonus_percent": 10,
            "transfer_tax_percent": 10,
            "max_balance": 100000000,
            "terminal_log_level": "INFO",
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=4)
        config = default
    else:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

    # Environment variables are authoritative for owner / co-owner IDs.
    env_owner = os.getenv("OWNER_ID")
    if env_owner and env_owner.isdigit():
        config["owner_id"] = int(env_owner)

    env_co_owners = os.getenv("CO_OWNERS")
    if env_co_owners:
        config["co_owner_ids"] = _parse_int_list(env_co_owners)

    env_guild_ids = os.getenv("GUILD_ID")
    if env_guild_ids:
        config["guild_ids"] = _parse_int_list(env_guild_ids)

    # Түвшнийг normalize хийх: терминал дээр харуулах лог түвшин.
    allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NONE", "OFF"}
    lvl = str(config.get("terminal_log_level", "INFO")).strip().upper()
    if lvl not in allowed:
        lvl = "INFO"
    config["terminal_log_level"] = lvl
    return config


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)
