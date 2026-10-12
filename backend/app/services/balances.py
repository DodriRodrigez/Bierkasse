"""Balance calculations.

Convention (documented once, used everywhere):

* ``Account`` balance          = Σ(SOLL) − Σ(HABEN) of its lines  (Aktivkonten).
* **Bestandskonto** types       = giro, cash, cc, member, external, transfer.
* ``Kassenbereich`` balance     = Σ(SOLL − HABEN) over its lines that hit a
  Bestandskonto.  Revenue/expense/clearing accounts do not carry a *balance*,
  they only move it — so they are ignored for the area balance while still
  being required to carry a kassenbereich (accounting dimension).
* Liquidität  = payment accounts (giro, cash, cc).
* Forderungen = member accounts (positive = members owe the Verbindung).
* Verbindlichkeiten = −Σ(external accounts).

Because every Bestandskonto line carries a Kassenbereich, the control equation

    Σ Kassenbereichsbestände == Liquidität + Forderungen − Verbindlichkeiten

holds by construction; any residual is surfaced as "nicht zugeordnet".
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account, Kassenbereich, Transaction, TransactionLine
from app.models.enums import AccountType, ApprovalStatus, Side

BESTANDSKONTO_TYPES = {
    AccountType.GIRO,
    AccountType.CASH,
    AccountType.CC,
    AccountType.MEMBER,
    AccountType.EXTERNAL,
    AccountType.TRANSFER,
}
PAYMENT_TYPES = {AccountType.GIRO, AccountType.CASH, AccountType.CC}
ZERO = Decimal("0.0000")


def _signed(side: Side, amount: Decimal) -> Decimal:
    return amount if side == Side.SOLL else -amount


def _base_stmt(semester_id: str | None, only_locked: bool):
    stmt = select(TransactionLine).join(Transaction, TransactionLine.transaction_id == Transaction.id)
    # Nur freigegebene Buchungen zählen in den Salden (eingereichte/abgelehnte nicht).
    stmt = stmt.where(Transaction.approval_status == ApprovalStatus.APPROVED)
    if semester_id:
        stmt = stmt.where(Transaction.semester_id == semester_id)
    if only_locked:
        stmt = stmt.where(Transaction.is_locked.is_(True))
    return stmt


def _sum_lines(lines) -> Decimal:
    total = ZERO
    for line in lines:
        total += _signed(line.side, line.amount)
    return total


def kassenbereich_balance(db: Session, kassenbereich_id: str, semester_id: str | None = None,
                          only_locked: bool = False) -> Decimal:
    stmt = (
        _base_stmt(semester_id, only_locked)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(TransactionLine.kassenbereich_id == kassenbereich_id)
        .where(Account.type.in_(BESTANDSKONTO_TYPES))
    )
    return _sum_lines(db.scalars(stmt))


def all_kassenbereich_balances(db: Session, semester_id: str | None = None,
                               only_locked: bool = False) -> dict[str, Decimal]:
    balances = {kb.id: ZERO for kb in db.scalars(select(Kassenbereich))}
    stmt = (
        _base_stmt(semester_id, only_locked)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(Account.type.in_(BESTANDSKONTO_TYPES))
    )
    for line in db.scalars(stmt):
        if line.kassenbereich_id in balances:
            balances[line.kassenbereich_id] += _signed(line.side, line.amount)
    return balances


def account_balance(db: Session, account_id: str, semester_id: str | None = None) -> Decimal:
    stmt = _base_stmt(semester_id, False).where(TransactionLine.account_id == account_id)
    return _sum_lines(db.scalars(stmt))


def payment_balances(db: Session, semester_id: str | None = None) -> list[tuple[Account, Decimal]]:
    accounts = db.scalars(
        select(Account).where(Account.type.in_(PAYMENT_TYPES)).order_by(Account.name)
    ).all()
    return [(acc, account_balance(db, acc.id, semester_id)) for acc in accounts]


def liquiditaet(db: Session, semester_id: str | None = None) -> Decimal:
    return sum((bal for _, bal in payment_balances(db, semester_id)), ZERO)


def forderungen(db: Session, semester_id: str | None = None) -> Decimal:
    stmt = (
        _base_stmt(semester_id, False)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(Account.type == AccountType.MEMBER)
    )
    return _sum_lines(db.scalars(stmt))


def verbindlichkeiten(db: Session, semester_id: str | None = None) -> Decimal:
    stmt = (
        _base_stmt(semester_id, False)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(Account.type == AccountType.EXTERNAL)
    )
    # liability = negative signed balance
    return -_sum_lines(db.scalars(stmt))


def control_equation(db: Session, semester_id: str | None = None) -> dict:
    balances = all_kassenbereich_balances(db, semester_id)
    sum_areas = sum(balances.values(), ZERO)
    expected = liquiditaet(db, semester_id) + forderungen(db, semester_id) - verbindlichkeiten(db, semester_id)
    return {
        "sum_kassenbereiche": sum_areas,
        "liquiditaet": liquiditaet(db, semester_id),
        "forderungen": forderungen(db, semester_id),
        "verbindlichkeiten": verbindlichkeiten(db, semester_id),
        "expected": expected,
        "difference": sum_areas - expected,
    }


def member_balance_by_kassenbereich(db: Session, user_id: str, semester_id: str | None = None) -> dict[str, Decimal]:
    """Per-area outstanding balance for a single member account."""
    stmt = (
        _base_stmt(semester_id, False)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(Account.user_id == user_id)
    )
    result: dict[str, Decimal] = {}
    for line in db.scalars(stmt):
        result[line.kassenbereich_id] = result.get(line.kassenbereich_id, ZERO) + _signed(line.side, line.amount)
    return result


def member_total_balance(db: Session, user_id: str, semester_id: str | None = None) -> Decimal:
    stmt = (
        _base_stmt(semester_id, False)
        .join(Account, TransactionLine.account_id == Account.id)
        .where(Account.user_id == user_id)
    )
    return _sum_lines(db.scalars(stmt))
