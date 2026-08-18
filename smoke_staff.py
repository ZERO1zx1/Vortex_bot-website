import sys, types, importlib

# Pre-mock external packages before any discord import.
mocks = ("supabase", "psutil", "motor", "asyncpg", "psycopg2",
         "config_manager", "database", "database.supabase_manager", "database.redis_manager")
for mod in mocks:
    if mod not in sys.modules:
        sys.modules[mod] = types.ModuleType(mod)

import discord  # real
import discord.ext  # noqa
from discord.ext import commands as real_commands  # noqa

# Verify adapter presence in both staff cogs
import inspect
from cogs import admin as admin_cog
from cogs import moderation as mod_cog
from cogs import games as games_cog

src_a = inspect.getsource(admin_cog.Admin)
src_m = inspect.getsource(mod_cog.Moderation)
assert "ctx = SlashContext(interaction)" in src_a, "admin adapter missing"
assert "ctx = SlashContext(interaction)" in src_m, "mod adapter missing"
print("ADMIN_SLASH_CONTEXT_OK")
print("MOD_SLASH_CONTEXT_OK")

# Verify apps_command decorators on all admin/moderation callbacks
import re
a_apps = re.findall(r"@app_commands\.command\(name\s*=\s*['\"]([^'\"]+)['\"]", src_a)
m_apps = re.findall(r"@app_commands\.command\(name\s*=\s*['\"]([^'\"]+)['\"]", src_m)
a_legacy = re.findall(r"@commands\.(hybrid_command|command)\(", src_a)
m_legacy = re.findall(r"@commands\.(hybrid_command|command)\(", src_m)
print("admin_apps:", sorted(a_apps), "legacy:", a_legacy)
print("mod_apps:", sorted(m_apps), "legacy:", m_legacy)
assert not a_legacy and not m_legacy, "legacy prefix commands remain"

# Verify permission checks use app_commands scope
assert "@app_commands.checks.has_permissions" in src_a and "@commands.has_permissions" not in src_a
assert "@app_commands.checks.has_permissions" in src_m and "@commands.has_permissions" not in src_m
print("PERMISSION_CHECKS_SLASH_ONLY_OK")

# Count games views to confirm the earlier fix still loads
view_classes = [name for name in dir(games_cog) if name.endswith("View")]
print("GAMES_VIEWS:", sorted(view_classes))
print("ALL_SMOKE_TESTS_PASSED")
