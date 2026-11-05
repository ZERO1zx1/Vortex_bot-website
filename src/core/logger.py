"""
Vortex Bot — Төвлөрсөн лог тохиргоо.

Бүх cog болон модулиуд энэ logger-ийг ашиглана.
`setup_logging()`-г main.py дотор нэг удаа дуудна.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import re
import sys
from pathlib import Path

# Repo root (src/-с 2 түвшин дээш)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = Path(os.getenv("LOG_DIR", REPO_ROOT / "logs"))

# ── Secret redaction ────────────────────────────────────────────────
# Defence in depth: no key is logged today, but a future change could leak
# one through a formatted message, an f-string or a traceback.  The filter
# runs on every record before it reaches a handler.
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(discord[_-]?token|bot[_-]?token|token|secret|secret[_-]?key|"
    r"password|passwd|api[_-]?key|apikey|access[_-]?key|private[_-]?key|"
    r"client[_-]?secret|authorization|auth)\b(\s*[:=]\s*)"
    r"(\"[^\"]*\"|'[^']*'|\S+)"
)
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}\b")
_RESEND_KEY_RE = re.compile(r"\bre_[A-Za-z0-9_-]{10,}\b")
_SUPABASE_SECRET_RE = re.compile(r"\bsb_secret_[A-Za-z0-9_-]{10,}\b")
_DISCORD_TOKEN_RE = re.compile(r"\b[MNO][A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{6}\.[A-Za-z0-9_-]{20,}\b")


def redact_secrets(text: str) -> str:
    """Replace secret-looking values in ``text`` with a placeholder."""
    if not text:
        return text
    text = _SECRET_ASSIGNMENT_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}<redacted>", text)
    text = _JWT_RE.sub("<redacted-jwt>", text)
    text = _RESEND_KEY_RE.sub("<redacted-key>", text)
    text = _SUPABASE_SECRET_RE.sub("<redacted-key>", text)
    text = _DISCORD_TOKEN_RE.sub("<redacted-token>", text)
    return text


class SecretRedactionFilter(logging.Filter):
    """Redact secrets from the formatted message of every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 — a broken record must not break logging
            return True
        redacted = redact_secrets(message)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def setup_logging(
    level: str | None = None,
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
) -> None:
    """
    Бүх лог-ийг тохируулах. Discord.py-ийн logger-ийг ч багтаана.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR). Default: INFO.
        log_file: Лог файлын нэр. Default: bot.log
        max_bytes: Файл бүрийн хамгийн их хэмжээ (rotating).
        backup_count: Хадгалах хуучин файлын тоо.
    """
    log_level = getattr(logging, (level or os.getenv("LOG_LEVEL", "INFO")).upper(), logging.INFO)
    log_path = LOG_DIR / (log_file or "bot.log")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Формат
    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    root.handlers.clear()

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(log_level)
    console.addFilter(SecretRedactionFilter())
    root.addHandler(console)

    # File handler (rotating)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(log_level)
        file_handler.addFilter(SecretRedactionFilter())
        root.addHandler(file_handler)
    except OSError as exc:
        root.warning("Файл руу лог бичих боломжгүй: %s", exc)

    # Discord.py-ийн спам-ыг багасгах
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Модульд зориулсан logger буцаана."""
    return logging.getLogger(name)