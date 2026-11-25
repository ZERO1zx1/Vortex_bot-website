"""UTC timestamp conversion for PostgreSQL rows and display strings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.database import DatabaseTimestamp

DB_FORMAT = "%Y-%m-%d %H:%M:%S"


def utcnow() -> datetime:
    """Timezone-aware UTC одоо."""
    return datetime.now(UTC)


def to_db(moment: datetime) -> DatabaseTimestamp:
    """datetime → repository-compatible UTC ISO text."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return DatabaseTimestamp(moment.astimezone(UTC).strftime(DB_FORMAT))


def to_db_text(value: str | datetime) -> str:
    """Normalize asyncpg datetime rows for display-facing models."""
    if isinstance(value, datetime):
        return str(to_db(value))
    return value


def from_db(value: str | datetime | None) -> datetime | None:
    """PostgreSQL datetime эсвэл ISO текст → timezone-aware UTC datetime.

    `YYYY-MM-DD HH:MM:SS`, `T` тусгаарлагч, `Z`, эерэг/сөрөг offset,
    микросекунд бүгдийг `datetime.fromisoformat` уншина.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        moment = value
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        return moment.astimezone(UTC)
    try:
        moment = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def seconds_until(moment: datetime | None) -> int:
    """Тухайн агшинд хүртэлх бүхэл секунд (аль хэдийн өнгөрсөн бол 0)."""
    if moment is None:
        return 0
    return max(0, int((moment - utcnow()).total_seconds()))


def seconds_since(moment: datetime | None) -> int:
    """Тухайн агшнаас хойш өнгөрсөн бүхэл секунд."""
    if moment is None:
        return 0
    return max(0, int((utcnow() - moment).total_seconds()))


def humanize_seconds(total: int) -> str:
    """`3725` → `1ц 2м`. Монгол хэлний богино хэлбэр."""
    total = max(0, int(total))
    hours, rem = divmod(total, 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return f"{hours}ц {minutes}м"
    if minutes:
        return f"{minutes}м {seconds}с"
    return f"{seconds}с"


def now_plus(seconds: int) -> datetime:
    return utcnow() + timedelta(seconds=seconds)
