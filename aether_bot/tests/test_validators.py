from __future__ import annotations

import pytest

import config
from core.exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
    InvalidBetError,
)
from utils.validators import parse_amount, parse_bet, parse_quantity


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1000", 1000),
        ("1,000", 1000),
        ("10k", 10_000),
        ("1.5m", 1_500_000),
        ("2b", 2_000_000_000),
        ("0.5k", 500),
        (500, 500),
    ],
)
def test_parse_quantity_formats(raw: str | int, expected: int) -> None:
    assert parse_quantity(raw) == expected


def test_all_and_half_use_balance() -> None:
    assert parse_quantity("all", balance=1234, allow_all=True) == 1234
    assert parse_quantity("half", balance=1235, allow_half=True) == 617
    assert parse_amount("all", balance=500, allow_all=True) == 500


def test_all_requires_permission_and_balance() -> None:
    with pytest.raises(InvalidAmountError, match="all"):
        parse_quantity("all")
    with pytest.raises(InvalidAmountError, match="half"):
        parse_quantity("half")


@pytest.mark.parametrize("raw", ["", "  ", "abc", "1.5", "-5", "1.2.3"])
def test_invalid_amounts_are_rejected(raw: str) -> None:
    with pytest.raises(InvalidAmountError):
        parse_amount(raw)


def test_minimum_and_maximum_are_enforced() -> None:
    with pytest.raises(InvalidAmountError, match="хамгийн багадаа"):
        parse_amount("0")
    with pytest.raises(InvalidAmountError, match="хамгийн ихдээ"):
        parse_amount("101", maximum=100)


def test_parse_bet_checks_balance_and_limits() -> None:
    assert parse_bet("all", balance=5000) == 5000
    assert parse_bet("half", balance=5000) == 2500
    with pytest.raises(InvalidBetError, match="хамгийн багадаа"):
        parse_bet(str(config.CASINO_MIN_BET - 1), balance=10_000)
    with pytest.raises(InsufficientFundsError, match="Wallet"):
        parse_bet("1000", balance=500)
