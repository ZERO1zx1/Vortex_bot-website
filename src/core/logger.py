"""
Vortex Bot — Төвлөрсөн лог тохиргоо.

Бүх cog болон модулиуд энэ logger-ийг ашиглана.
`setup_logging()`-г main.py дотор нэг удаа дуудна.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional


# Repo root (src/-с 2 түвшин дээш)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = Path(os.getenv("LOG_DIR", REPO_ROOT / "logs"))


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
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
    root.addHandler(console)

    # File handler (rotating)
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        file_handler.setFormatter(fmt)
        file_handler.setLevel(log_level)
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