"""
Vortex Bot — Custom exceptions.

Database, config, болон бусад модулиудад зориулсан тодорхой алдаанууд.
"""
from __future__ import annotations


class VortexError(Exception):
    """Бүх custom алдааны үндсэн класс."""


# ── Database ────────────────────────────────────────────────
class DatabaseError(VortexError):
    """Database-тэй холбоотой ерөнхий алдаа."""


class DatabasePermissionError(DatabaseError):
    """
    PostgreSQL 42501 — permission denied for table.
    Шалтгаан: GRANT дутуу, эсвэл буруу key (anon instead of service_role).
    """


class DatabaseSchemaError(DatabaseError):
    """
    PGRST202/PGRST205 / 42P01 — RPC эсвэл table олдсонгүй.
    Шалтгаан: Migration ажиллуулаагүй.
    """


class DatabaseUnavailableError(DatabaseError):
    """
    Network, timeout, 5xx — retry хийх боломжтой алдаа.
    """


# ── Config ──────────────────────────────────────────────────
class ConfigError(VortexError):
    """config.json эсвэл .env-тэй холбоотой алдаа."""


class MissingEnvVarError(ConfigError):
    """Шаардлагатай environment variable байхгүй."""


# ── Cog ─────────────────────────────────────────────────────
class CogLoadError(VortexError):
    """Cog ачаалахад гарсан алдаа."""


# ── Permission / Auth ───────────────────────────────────────
class PermissionDeniedError(VortexError):
    """Discord permission эсвэл role шалгахад гарсан алдаа."""


class UserNotFoundError(VortexError):
    """Хэрэглэгч database-д олдсонгүй."""


# ── Economy / Game ──────────────────────────────────────────
class InsufficientFundsError(VortexError):
    """Хэрэглэгчийн баланс хүрэлцэхгүй."""


class InsufficientStockError(VortexError):
    """Shop-д stock хүрэлцэхгүй."""


class CooldownError(VortexError):
    """Command хэт хурдан дуудагдсан."""
