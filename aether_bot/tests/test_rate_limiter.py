from __future__ import annotations

import pytest

from core.rate_limiter import RateLimiter


async def test_amount_above_capacity_is_rejected() -> None:
    limiter = RateLimiter(max_rate=2)
    with pytest.raises(ValueError, match="amount <= capacity"):
        await limiter.acquire(3)


def test_zero_burst_is_rejected() -> None:
    with pytest.raises(ValueError, match="burst"):
        RateLimiter(max_rate=2, burst=0)


def test_non_positive_window_is_rejected() -> None:
    with pytest.raises(ValueError, match="per_seconds"):
        RateLimiter(max_rate=2, per_seconds=0)
