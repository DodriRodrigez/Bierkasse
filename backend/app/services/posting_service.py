"""Automatic, balanced postings for the feature modules.

Every function here produces a *balanced* booking through
:func:`accounting_service.create_transaction` — never a one-sided line.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ValidationError
from app.core.money import to_decimal
from app.models.entities import (
    Account,
    Beverage,
    Delivery,
    Event,
    ExpenseRefundRequest,
    RingbrettSession,
    User,
)
from app.models.enums import (
    AccountType,
    EventType,
    PayerType,
    RefundStatus,
    RingColor,
    Side,
    TransactionCategory,
)
from app.services import accounting_service
from app.services.accounting_service import LineInput

DEFAULT_RING_PRICE = {RingColor.RED: Decimal("0.70"), RingColor.YELLOW: Decimal("1.00")}


def _ring_price(db: Session, color: RingColor) -> Decimal:
    beverage = db.scalar(
        select(Beverage).where(Beverage.ring_color == color, Beverage.is_active.is_(True))
    )
    return beverage.ring_price if beverage else DEFAULT_RING_PRICE[color]


def _account_by_type(db: Session, acc_type: AccountType, name_contains: str | None = None) -> Account:
    stmt = select(Account).where(Account.type == acc_type)
    if name_contains:
        stmt = stmt.where(Account.name.contains(name_contains))
    account = db.scalars(stmt).first()
    if not account:
        raise ValidationError(f"Konto vom Typ '{acc_type.value}' fehlt (Seed ausführen).")
    return account


def ring_price_summary(db: Session) -> dict:
    red = _ring_price(db, RingColor.RED)
    yellow = _ring_price(db, RingColor.YELLOW)
    return {"red": red, "yellow": yellow}


# --------------------------------------------------------------------------
# Ringbrett
# --------------------------------------------------------------------------
def post_ringbrett(db: Session, session: RingbrettSession, user: User) -> list[str]:
    if session.transaction_id:
        raise ValidationError("Diese Zählung wurde bereits verbucht.")
    red = _ring_price(db, RingColor.RED)
    yellow = _ring_price(db, RingColor.YELLOW)
    revenue = _account_by_type(db, AccountType.REVENUE, "erlös")
    kb_id = session.kassenbereich_id

    lines: list[LineInput] = []
    total = Decimal("0.0000")
    for entry in session.entries:
        amount = to_decimal(entry.red_rings) * red + to_decimal(entry.yellow_rings) * yellow
        if amount <= 0:
            continue
        total += amount
        lines.append(
            LineInput(
                account_id=entry.user.account.id,
                side=Side.SOLL,
                amount=amount,
                kassenbereich_id=kb_id,
                member_id=entry.user_id,
                description=f"{entry.user.full_name}: {entry.red_rings} rot + {entry.yellow_rings} gelb",
            )
        )
    if not lines:
        raise ValidationError("Keine Buchungszeilen mit Ringen > 0.")
    lines.append(
        LineInput(revenue.id, Side.HABEN, total, kb_id, description="Getränkeerlös Ringbrett")
    )
    result = accounting_service.create_transaction(
        db,
        date_=session.date,
        description=f"Ringbrett-Zählung Nr. {session.zaehlungsnummer}",
        category=TransactionCategory.RB,
        lines=lines,
        user=user,
        semester_id=session.semester_id,
        lock=True,
    )
    session.transaction_id = result.transaction.id
    session.status = "posted"
    db.flush()
    return result.warnings


# --------------------------------------------------------------------------
# Veranstaltung (Ringgläser) — CC-Kasse / Mitglied
# --------------------------------------------------------------------------
def post_event(db: Session, event: Event, user: User) -> list[str]:
    if event.transaction_id:
        raise ValidationError("Diese Veranstaltung wurde bereits verbucht.")
    red = _ring_price(db, RingColor.RED)
    yellow = _ring_price(db, RingColor.YELLOW)
    gross = to_decimal(event.red_glasses) * red + to_decimal(event.yellow_glasses) * yellow
    amount = max(gross - to_decimal(event.donation), Decimal("0.0000"))
    if amount <= 0:
        raise ValidationError("Veranstaltungsbetrag ist 0.")

    kb_id = event.kassenbereich_id
    if event.payer_type == PayerType.MEMBER and event.payer_user_id:
        member = db.get(User, event.payer_user_id)
        if not member or not member.account:
            raise ValidationError("Zahler-Mitglied hat kein Konto.")
        lines = [
            LineInput(member.account.id, Side.SOLL, amount, kb_id, member_id=member.id,
                      description=f"Ringgläser {event.name}"),
            LineInput(_account_by_type(db, AccountType.REVENUE, "erlös").id, Side.HABEN, amount, kb_id,
                      description="Getränkeerlös Veranstaltung"),
        ]
    else:
        # CC-Kasse bezahlt aus ihrem Barkonto
        cash = db.scalar(
            select(Account).where(Account.type == AccountType.CASH, Account.name.contains("CC"))
        ) or _account_by_type(db, AccountType.CASH)
        expense = db.scalar(
            select(Account).where(Account.type == AccountType.EXPENSE, Account.name.contains("bewirtung"))
        ) or _account_by_type(db, AccountType.EXPENSE)
        lines = [
            LineInput(expense.id, Side.SOLL, amount, kb_id, description=f"Bewirtung {event.name}"),
            LineInput(cash.id, Side.HABEN, amount, kb_id, description=f"Zahlung CC-Kasse {event.name}"),
        ]

    result = accounting_service.create_transaction(
        db,
        date_=event.date,
        description=f"Veranstaltung: {event.name}",
        category=TransactionCategory.CB,
        lines=lines,
        user=user,
        semester_id=event.semester_id,
        tags=[tag.name for tag in event.tags],
        lock=True,
    )
    event.transaction_id = result.transaction.id
    event.is_posted = True
    db.flush()
    return result.warnings


# --------------------------------------------------------------------------
# Getränkelieferung (Aufwand)
# --------------------------------------------------------------------------
def post_delivery(db: Session, delivery: Delivery, user: User) -> list[str]:
    if delivery.transaction_id:
        raise ValidationError("Diese Lieferung wurde bereits verbucht.")
    total = sum(
        (to_decimal(i.purchase_price) * (i.crates * (i.beverage.bottles_per_crate if i.beverage else 20))
         + to_decimal(i.purchase_price) * i.single_bottles + to_decimal(i.deposit))
        for i in delivery.items
    )
    total = to_decimal(total)
    if total <= 0:
        raise ValidationError("Liefersumme ist 0.")
    expense = _account_by_type(db, AccountType.EXPENSE, "einkauf")
    kb_id = delivery.kassenbereich_id
    if not kb_id:
        raise ValidationError("Lieferung ohne Kassenbereich.")
    if delivery.payment_account_id:
        counter = db.get(Account, delivery.payment_account_id)
    else:
        counter = _account_by_type(db, AccountType.EXTERNAL, "lieferant")
    lines = [
        LineInput(expense.id, Side.SOLL, total, kb_id, description="Getränkeeinkauf"),
        LineInput(counter.id, Side.HABEN, total, kb_id, description=f"Zahlung {delivery.supplier}"),
    ]
    result = accounting_service.create_transaction(
        db,
        date_=delivery.date,
        description=f"Getränkelieferung {delivery.supplier}",
        category=TransactionCategory.BL,
        lines=lines,
        user=user,
        semester_id=delivery.semester_id,
        lock=True,
    )
    delivery.transaction_id = result.transaction.id
    delivery.is_posted = True
    db.flush()
    return result.warnings


# --------------------------------------------------------------------------
# Auslagenerstattung
# --------------------------------------------------------------------------
def post_refund(db: Session, refund: ExpenseRefundRequest, user: User) -> None:
    if refund.transaction_id:
        raise ValidationError("Diese Erstattung wurde bereits verbucht.")
    expense = _account_by_type(db, AccountType.EXPENSE, "auslage")
    online = _account_by_type(db, AccountType.GIRO)
    kb_id = refund.kassenbereich_id
    lines = [
        LineInput(expense.id, Side.SOLL, refund.amount, kb_id, description=refund.description),
        LineInput(online.id, Side.HABEN, refund.amount, kb_id, description="Erstattung Auslage"),
    ]
    result = accounting_service.create_transaction(
        db,
        date_=refund.date,
        description=f"Auslagenerstattung: {refund.description[:80]}",
        category=TransactionCategory.MISC,
        lines=lines,
        user=user,
        lock=True,
    )
    refund.transaction_id = result.transaction.id
    refund.status = RefundStatus.PAID
    db.flush()
