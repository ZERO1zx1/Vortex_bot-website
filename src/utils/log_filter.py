"""Rate-limiting logging filter for identical infrastructure messages.

While the database is broken, cogs may emit the same error from many events
in a short window.  This filter keeps the first ``max_identical`` messages,
then suppresses repeats with a compact counter so the log stays readable
without hiding new/different failures.
"""

import logging
import time

DEFAULT_QUIET_SECONDS = 300


class RateLimitFilter(logging.Filter):
    """Suppress bursts of identical log records (same logger + message).

    Usage:

        handler.addFilter(RateLimitFilter(max_identical=3, quiet=300))
    """

    def __init__(self, max_identical: int = 3, quiet: float = DEFAULT_QUIET_SECONDS):
        super().__init__()
        self._max_identical = max_identical
        self._quiet = quiet
        self._state: dict[tuple, tuple[int, float, str]] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        key = (record.name, record.msg)
        count, first_seen, suppressed = self._state.get(key, (0, 0.0, ""))
        now = time.monotonic()
        if now - first_seen >= self._quiet:
            count = 0
            first_seen = 0.0
            suppressed = ""
        count += 1
        self._state[key] = (count, first_seen if first_seen else now, suppressed)
        if count <= self._max_identical:
            return True
        if count == self._max_identical + 1 or not suppressed:
            suppressed = (f"({count - self._max_identical} identical "
                          f"messages suppressed)")
            self._state[key] = (count, first_seen, suppressed)
            record.msg = f"{record.msg} {suppressed}"
            return True
        if count % 100 == 0:
            suppressed = (f"({count - self._max_identical} identical "
                          f"messages suppressed)")
            self._state[key] = (count, first_seen, suppressed)
            record.msg = f"{record.msg} {suppressed}"
            return True
        return False