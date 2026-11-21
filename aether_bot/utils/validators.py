"""Хэрэглэгчийн оруулсан дүн, бооцоог задлах туслах.

Discord prefix команд дээр `a!deposit 10k`, `a!slots all`, `a!pay @user 1.5m`
гэх мэт бичих боломжтой. Бүх утга эерэг бүхэл тоо болж хувирна.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

import config
from core.exceptions import (
    InsufficientFundsError,
    InvalidAmountError,
    InvalidBetError,
    ValidationError,
)

_SUFFIXES = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
    "t": 1_000_000_000_000,
}

_CLEAN = str.maketrans("", "", ",_ ")


def parse_quantity(
    raw: str | int,
    *,
    balance: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
    allow_all: bool = False,
    allow_half: bool = False,
    error: type[ValidationError] = InvalidAmountError,
) -> int:
    """`"10k"`, `"1.5m"`, `"all"`, `"half"` зэргийг бүхэл тоо болгоно.

    `error` нь ямар домайн алдаа шидэхыг тодорхойлно (`InvalidBetError`
    гэх мэт). Бооцоонд `all`/`half` зөвхөн `balance` өгсөн үед л зөвшөөрнө.
    """
    if isinstance(raw, int):
        return _validate(raw, minimum=minimum, maximum=maximum, error=error)

    text = str(raw).strip().lower().translate(_CLEAN)
    if not text:
        raise error("✦ Дүн хоосон байна. Жишээ: `1000`, `10k`, `1.5m`, `all`.")

    if text in {"all", "бүгд"}:
        if not allow_all or balance is None:
            raise error("✦ `all` энд ашиглах боломжгүй.")
        return _validate(
            max(0, int(balance)), minimum=minimum, maximum=maximum, error=error
        )
    if text in {"half", "хагас"}:
        if not allow_half or balance is None:
            raise error("✦ `half` энд ашиглах боломжгүй.")
        return _validate(
            max(0, int(balance) // 2), minimum=minimum, maximum=maximum, error=error
        )

    multiplier = 1
    if text[-1] in _SUFFIXES:
        multiplier = _SUFFIXES[text[-1]]
        text = text[:-1]
    if not text:
        raise error("✦ Дүн буруу форматтай байна.")

    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise error(f"✦ `{raw}` нь тоо биш байна.") from exc
    if not value.is_finite() or value < 0:
        raise error("✦ Дүн эерэг тоо байх ёстой.")

    amount = value * multiplier
    if amount != amount.to_integral_value():
        raise error("✦ Дүн бүхэл тоо болох ёстой.")
    return _validate(int(amount), minimum=minimum, maximum=maximum, error=error)


def _validate(
    amount: int,
    *,
    minimum: int,
    maximum: int | None,
    error: type[ValidationError],
) -> int:
    if amount < minimum:
        raise error(f"✦ Дүн хамгийн багадаа **{minimum:,}** байх ёстой.")
    if maximum is not None and amount > maximum:
        raise error(f"✦ Дүн хамгийн ихдээ **{maximum:,}** байх ёстой.")
    return amount


def parse_amount(
    raw: str | int,
    *,
    balance: int | None = None,
    minimum: int = 1,
    maximum: int | None = None,
    allow_all: bool = False,
    allow_half: bool = False,
) -> int:
    """Ерөнхий дүн (deposit/withdraw/transfer)."""
    return parse_quantity(
        raw,
        balance=balance,
        minimum=minimum,
        maximum=maximum,
        allow_all=allow_all,
        allow_half=allow_half,
        error=InvalidAmountError,
    )


def parse_bet(
    raw: str | int,
    *,
    balance: int,
    minimum: int = config.CASINO_MIN_BET,
    maximum: int = config.CASINO_MAX_BET,
) -> int:
    """Казиногийн бооцоо: `all`, `half`, `10k` бүгд болно."""
    amount = parse_quantity(
        raw,
        balance=balance,
        minimum=minimum,
        maximum=maximum,
        allow_all=True,
        allow_half=True,
        error=InvalidBetError,
    )
    if amount > balance:
        raise InsufficientFundsError(
            f"✦ Бооцоо **{amount:,}** ⛃ боловч Wallet дээр зөвхөн "
            f"**{balance:,}** ⛃ байна."
        )
    return amount
