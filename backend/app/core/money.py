"""Exact money handling.

Money is ALWAYS a ``decimal.Decimal`` with exactly 4 fractional digits.
Although the domain spec is written as DECIMAL(10,4), we widen to 12,4 so that
sums over a semester do not overflow the integer part.

Storage strategy (both exact, no float anywhere):
* SQLite  -> scaled integers (amount * 10_000) so that ``SUM()`` stays exact.
* Other   -> native NUMERIC(12,4).
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import BigInteger, Numeric, TypeDecorator

SCALE = Decimal(10_000)
QUANT = Decimal("0.0001")


def to_decimal(value) -> Decimal:
    """Coerce any numeric input to an exact 4-decimal Decimal."""
    if isinstance(value, Decimal):
        dec = value
    elif isinstance(value, int):
        dec = Decimal(value)
    else:
        # str() first: never let a binary float leak in.
        dec = Decimal(str(value))
    return dec.quantize(QUANT, rounding=ROUND_HALF_UP)


class MoneyType(TypeDecorator):
    impl = Numeric(12, 4)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(BigInteger)
        return dialect.type_descriptor(Numeric(12, 4))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        dec = to_decimal(value)
        if dialect.name == "sqlite":
            return int((dec * SCALE).to_integral_value(rounding=ROUND_HALF_UP))
        return dec

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "sqlite":
            return (Decimal(int(value)) / SCALE).quantize(QUANT)
        return to_decimal(value)


def fmt_eur(value: Decimal | int | float | None) -> str:
    """German currency formatting, e.g. 1234.5 -> '1.234,50 €'."""
    dec = to_decimal(value or 0)
    s = f"{dec:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"
