import json
import os
from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = "config.json"


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
    """
    if not os.path.exists(CONFIG_FILE):
        default = {
            "owner_id": None,
            "co_owner_ids": [],
            "prefix": "!",
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
        return default

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Environment variables are authoritative for owner / co-owner IDs.
    env_owner = os.getenv("OWNER_ID")
    if env_owner and env_owner.isdigit():
        config["owner_id"] = int(env_owner)

    env_co_owners = os.getenv("CO_OWNERS")
    if env_co_owners:
        config["co_owner_ids"] = _parse_int_list(env_co_owners)

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
