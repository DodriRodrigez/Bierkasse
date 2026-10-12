"""The 10 acceptance tests from the Kassenbereich specification."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.entities import User
from app.models.enums import Side, SystemRole, TransactionCategory
from app.services import accounting_service, balances
from app.services.accounting_service import LineInput

D = date(2026, 11, 1)


def _admin(db) -> User:
    return db.scalar(select(User).where(User.system_role == SystemRole.ADMIN))


def _book(db, world, lines, description="Test", category=TransactionCategory.MISC, lock=False):
    return accounting_service.create_transaction(
        db, date_=D, description=description, category=category, lines=lines,
        user=_admin(db), semester_id=world.semester.id, lock=lock,
    )


def _fund_online_1000(world, db):
    """1000 € on the online account, split 600 CC / 400 Bier."""
    online = world.account("Onlinekonto")
    eq = world.account("Eigenkapital")
    _book(
        db, world,
        [
            LineInput(online.id, Side.SOLL, Decimal("600"), world.kb["CC"].id),
            LineInput(online.id, Side.SOLL, Decimal("400"), world.kb["BIER"].id),
            LineInput(eq.id, Side.HABEN, Decimal("1000"), world.kb["ALG"].id),
        ],
        description="Zuordnung Onlinekonto",
    )


def test_1_and_2_onlinekonto_and_assignment(db, world):
    _fund_online_1000(world, db)
    db.flush()
    assert balances.account_balance(db, world.account("Onlinekonto").id) == Decimal("1000.0000")
    assert balances.kassenbereich_balance(db, world.kb["CC"].id) == Decimal("600.0000")
    assert balances.kassenbereich_balance(db, world.kb["BIER"].id) == Decimal("400.0000")


def test_3_expense_reduces_both_online_and_bierkasse(db, world):
    _fund_online_1000(world, db)
    online, expense = world.account("Onlinekonto"), world.account("Aufwand")
    bier = world.kb["BIER"].id
    _book(db, world, [
        LineInput(expense.id, Side.SOLL, Decimal("100"), bier),
        LineInput(online.id, Side.HABEN, Decimal("100"), bier),
    ])
    db.flush()
    assert balances.account_balance(db, online.id) == Decimal("900.0000")
    assert balances.kassenbereich_balance(db, bier) == Decimal("300.0000")


def test_4_cc_expense_does_not_change_bierkasse(db, world):
    _fund_online_1000(world, db)
    _book(db, world, [
        LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("100"), world.kb["CC"].id),
        LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("100"), world.kb["CC"].id),
    ])
    db.flush()
    assert balances.kassenbereich_balance(db, world.kb["BIER"].id) == Decimal("400.0000")
    assert balances.kassenbereich_balance(db, world.kb["CC"].id) == Decimal("500.0000")


def test_5_and_6_member_owes_two_areas(db, world):
    member = db.scalar(select(User).where(User.system_role == SystemRole.MITGLIED))
    member_acc = member.account
    revenue = world.account("Getränkeerlös")
    _book(db, world, [
        LineInput(member_acc.id, Side.SOLL, Decimal("25"), world.kb["BIER"].id, member_id=member.id),
        LineInput(revenue.id, Side.HABEN, Decimal("25"), world.kb["BIER"].id),
    ])
    _book(db, world, [
        LineInput(member_acc.id, Side.SOLL, Decimal("10"), world.kb["CC"].id, member_id=member.id),
        LineInput(revenue.id, Side.HABEN, Decimal("10"), world.kb["CC"].id),
    ])
    db.flush()
    by_area = balances.member_balance_by_kassenbereich(db, member.id)
    total = balances.member_total_balance(db, member.id)
    assert by_area[world.kb["BIER"].id] == Decimal("25.0000")
    assert by_area[world.kb["CC"].id] == Decimal("10.0000")
    assert total == Decimal("35.0000")
    assert sum(by_area.values()) == total


def test_7_negative_area_warns_but_does_not_block(db, world):
    _fund_online_1000(world, db)
    bier = world.kb["BIER"].id
    lines = [
        LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("500"), bier),
        LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("500"), bier),
    ]
    preview = accounting_service.preview(db, lines, world.semester.id)
    bier_preview = next(a for a in preview["areas"] if a["kassenbereich_id"] == bier)
    assert bier_preview["after"] == Decimal("-100.0000")
    assert bier_preview["overdrawn"] is True
    assert preview["warnings"]

    result = _book(db, world, lines, description="Überziehung Bierkasse")
    db.flush()
    assert result.warnings
    assert balances.kassenbereich_balance(db, bier) == Decimal("-100.0000")


def test_8_internal_transfer_leaves_liquidity_untouched(db, world):
    _fund_online_1000(world, db)
    db.flush()
    liquidity_before = balances.liquiditaet(db, world.semester.id)
    accounting_service.internal_transfer(
        db,
        from_kassenbereich_id=world.kb["CC"].id,
        to_kassenbereich_id=world.kb["BIER"].id,
        amount=Decimal("100"),
        date_=D,
        user=_admin(db),
        semester_id=world.semester.id,
    )
    db.flush()
    assert balances.liquiditaet(db, world.semester.id) == liquidity_before
    assert balances.kassenbereich_balance(db, world.kb["CC"].id) == Decimal("500.0000")
    assert balances.kassenbereich_balance(db, world.kb["BIER"].id) == Decimal("500.0000")


def test_9_split_invoice_across_areas(db, world):
    _fund_online_1000(world, db)
    online, expense = world.account("Onlinekonto"), world.account("Aufwand")
    _book(db, world, [
        LineInput(expense.id, Side.SOLL, Decimal("100"), world.kb["ALG"].id, description="Rechnung"),
        LineInput(online.id, Side.HABEN, Decimal("70"), world.kb["CC"].id, description="Anteil CC"),
        LineInput(online.id, Side.HABEN, Decimal("30"), world.kb["BIER"].id, description="Anteil Bier"),
    ])
    db.flush()
    assert balances.kassenbereich_balance(db, world.kb["CC"].id) == Decimal("530.0000")
    assert balances.kassenbereich_balance(db, world.kb["BIER"].id) == Decimal("370.0000")
    assert balances.account_balance(db, online.id) == Decimal("900.0000")


def test_10_locked_assignment_only_changeable_by_storno(db, world):
    _fund_online_1000(world, db)
    bier = world.kb["BIER"].id
    result = _book(db, world, [
        LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("100"), bier),
        LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("100"), bier),
    ], lock=True)
    db.flush()
    assert balances.kassenbereich_balance(db, bier) == Decimal("300.0000")

    storno = accounting_service.stornate(db, result.transaction, "Korrektur", _admin(db))
    db.flush()
    assert storno.is_storno is True
    assert storno.storno_reference_id == result.transaction.id
    assert balances.kassenbereich_balance(db, bier) == Decimal("400.0000")
