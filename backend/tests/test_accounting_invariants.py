"""Double-entry invariants and exact money handling."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError, ValidationError
from app.core.money import to_decimal
from app.models.entities import User
from app.models.enums import Side, SystemRole, TransactionCategory
from app.services import accounting_service, balances
from app.services.accounting_service import LineInput

D = date(2026, 11, 1)


def _admin(db) -> User:
    return db.scalar(select(User).where(User.system_role == SystemRole.ADMIN))


def test_unbalanced_booking_is_rejected(db, world):
    online, expense = world.account("Onlinekonto"), world.account("Aufwand")
    with pytest.raises(ValidationError):
        accounting_service.create_transaction(
            db, date_=D, description="Unbalanced", category=TransactionCategory.MISC,
            lines=[
                LineInput(expense.id, Side.SOLL, Decimal("100"), world.kb["CC"].id),
                LineInput(online.id, Side.HABEN, Decimal("90"), world.kb["CC"].id),
            ],
            user=_admin(db), semester_id=world.semester.id,
        )


def test_single_line_is_rejected(db, world):
    with pytest.raises(ValidationError):
        accounting_service.create_transaction(
            db, date_=D, description="One line", category=TransactionCategory.MISC,
            lines=[LineInput(world.account("Onlinekonto").id, Side.SOLL, Decimal("1"), world.kb["CC"].id)],
            user=_admin(db), semester_id=world.semester.id,
        )


def test_zero_or_negative_amount_is_rejected(db, world):
    with pytest.raises(ValidationError):
        accounting_service.create_transaction(
            db, date_=D, description="Zero", category=TransactionCategory.MISC,
            lines=[
                LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("0"), world.kb["CC"].id),
                LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("0"), world.kb["CC"].id),
            ],
            user=_admin(db), semester_id=world.semester.id,
        )


def test_booking_outside_semester_is_rejected(db, world):
    with pytest.raises(ValidationError):
        accounting_service.create_transaction(
            db, date_=date(2020, 1, 1), description="Wrong year", category=TransactionCategory.MISC,
            lines=[
                LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("1"), world.kb["CC"].id),
                LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("1"), world.kb["CC"].id),
            ],
            user=_admin(db), semester_id=world.semester.id,
        )


def test_double_storno_is_rejected(db, world):
    result = accounting_service.create_transaction(
        db, date_=D, description="To storno", category=TransactionCategory.MISC,
        lines=[
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("5"), world.kb["CC"].id),
            LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("5"), world.kb["CC"].id),
        ],
        user=_admin(db), semester_id=world.semester.id,
    )
    db.flush()
    accounting_service.stornate(db, result.transaction, "erste", _admin(db))
    db.flush()
    with pytest.raises(ConflictError):
        accounting_service.stornate(db, result.transaction, "zweite", _admin(db))


def test_money_is_exact_decimal(db, world):
    # 0.7 + 0.7 + 0.7 must be exactly 2.1, never 2.0999999...
    total = to_decimal("0.7") + to_decimal("0.7") + to_decimal("0.7")
    assert total == Decimal("2.1000")
    result = accounting_service.create_transaction(
        db, date_=D, description="Exact money", category=TransactionCategory.MISC,
        lines=[
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("0.70"), world.kb["CC"].id),
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("0.70"), world.kb["CC"].id),
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("0.70"), world.kb["CC"].id),
            LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("2.10"), world.kb["CC"].id),
        ],
        user=_admin(db), semester_id=world.semester.id,
    )
    db.flush()
    assert result.transaction.lines[3].amount == Decimal("2.1000")
