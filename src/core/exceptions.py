"""
Vortex Bot — Custom exceptions.

Database, config, болон бусад модулиудад зориулсан тодорхой алдаанууд.
"""
from __future__ import annotations


class VortexError(Exception):
    """Бүх custom алдааны үндсэн класс."""
    pass


# ── Database ────────────────────────────────────────────────
class DatabaseError(VortexError):
    """Database-тэй холбоотой ерөнхий алдаа."""
    pass


class DatabasePermissionError(DatabaseError):
    """
    PostgreSQL 42501 — permission denied for table.
    Шалтгаан: GRANT дутуу, эсвэл буруу key (anon instead of service_role).
    """
    pass


class DatabaseSchemaError(DatabaseError):
    """
    PGRST205 / 42P01 — table олдсонгүй.
    Шалтгаан: Migration ажиллуулаагүй.
    """
    pass


class DatabaseUnavailableError(DatabaseError):
    """
    Network, timeout, 5xx — retry хийх боломжтой алдаа.
    """
    pass


# ── Config ──────────────────────────────────────────────────
class ConfigError(VortexError):
    """config.json эсвэл .env-тэй холбоотой алдаа."""
    pass


class MissingEnvVarError(ConfigError):
    """Шаардлагатай environment variable байхгүй."""
    pass


# ── Cog ─────────────────────────────────────────────────────
class CogLoadError(VortexError):
    """Cog ачаалахад гарсан алдаа."""
    pass


# ── Permission / Auth ───────────────────────────────────────
class PermissionDeniedError(VortexError):
    """Discord permission эсвэл role шалгахад гарсан алдаа."""
    pass


class UserNotFoundError(VortexError):
    """Хэрэглэгч database-д олдсонгүй."""
    pass


# ── Economy / Game ──────────────────────────────────────────
class InsufficientFundsError(VortexError):
    """Хэрэглэгчийн баланс хүрэлцэхгүй."""
    pass


class InsufficientStockError(VortexError):
    """Shop-д stock хүрэлцэхгүй."""
    pass


class CooldownError(VortexError):
    """Command хэт хурдан дуудагдсан."""
    pass