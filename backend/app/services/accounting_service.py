"""Booking (Buchung) domain service — the single place where the double-entry
invariants are enforced.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.money import to_decimal
from app.models.entities import (
    Account,
    AuditLog,
    Kassenbereich,
    Tag,
    Transaction,
    TransactionLine,
    User,
)
from app.core.permissions import BOOKING_APPROVE, has_permission
from app.models.base import utcnow
from app.models.enums import AccountType, ApprovalStatus, AuditAction, Side, TransactionCategory
from app.services import balances


@dataclass
class LineInput:
    account_id: str
    side: Side
    amount: Decimal
    kassenbereich_id: str
    member_id: str | None = None
    description: str | None = None
    event_id: str | None = None


@dataclass
class TransactionResult:
    transaction: Transaction
    warnings: list[str] = field(default_factory=list)


def _next_sequential_number(db: Session) -> int:
    current = db.scalar(select(func.max(Transaction.sequential_number)))
    return int(current or 0) + 1


def _resolve_semester(db: Session, semester_id: str | None, booking_date: date):
    from app.models.entities import Semester
    from app.models.enums import SemesterStatus

    if semester_id:
        semester = db.get(Semester, semester_id)
        if not semester:
            raise NotFoundError("Semester nicht gefunden.")
    else:
        semester = db.scalar(select(Semester).where(Semester.status == SemesterStatus.ACTIVE))
        if not semester:
            raise ValidationError("Kein aktives Semester vorhanden.")
    if not (semester.start_date <= booking_date <= semester.end_date):
        raise ValidationError(
            f"Buchungsdatum {booking_date} liegt außerhalb des Semesters {semester.name}."
        )
    return semester


def _validate_lines(db: Session, lines: list[LineInput]) -> tuple[Decimal, Decimal]:
    if len(lines) < 2:
        raise ValidationError("Eine Buchung benötigt mindestens zwei Buchungszeilen.")
    total_soll = Decimal("0.0000")
    total_haben = Decimal("0.0000")
    for line in lines:
        amount = to_decimal(line.amount)
        if amount <= 0:
            raise ValidationError("Beträge müssen größer als 0 sein.")
        account = db.get(Account, line.account_id)
        if not account:
            raise NotFoundError(f"Konto {line.account_id} nicht gefunden.")
        kb = db.get(Kassenbereich, line.kassenbereich_id)
        if not kb:
            raise NotFoundError(f"Kassenbereich {line.kassenbereich_id} nicht gefunden.")
        if not kb.is_active:
            raise ValidationError(f"Kassenbereich '{kb.name}' ist deaktiviert.")
        if line.side == Side.SOLL:
            total_soll += amount
        else:
            total_haben += amount
    if to_decimal(total_soll) != to_decimal(total_haben):
        raise ValidationError(
            f"Buchung nicht ausgeglichen: SOLL {total_soll} ≠ HABEN {total_haben}."
        )
    return to_decimal(total_soll), to_decimal(total_haben)


def create_transaction(
    db: Session,
    *,
    date_: date,
    description: str,
    category: TransactionCategory,
    lines: list[LineInput],
    user: User,
    semester_id: str | None = None,
    tags: list[str] | None = None,
    receipt_status=None,
    is_internal_transfer: bool = False,
    lock: bool = False,
    auto_approve: bool | None = None,
) -> TransactionResult:
    _validate_lines(db, lines)
    semester = _resolve_semester(db, semester_id, date_)

    # Wer freigeben darf, bucht direkt; alle anderen reichen zur Freigabe ein.
    approved = auto_approve if auto_approve is not None else has_permission(user.system_role, BOOKING_APPROVE)

    txn = Transaction(
        date=date_,
        description=description,
        category=category,
        semester_id=semester.id,
        created_by_id=user.id,
        is_internal_transfer=is_internal_transfer,
        is_locked=bool(lock and approved),
        receipt_status=receipt_status,
        sequential_number=_next_sequential_number(db),
        approval_status=ApprovalStatus.APPROVED if approved else ApprovalStatus.SUBMITTED,
        approved_by_id=user.id if approved else None,
        approved_at=utcnow() if approved else None,
    )
    db.add(txn)
    db.flush()

    for line in lines:
        db.add(
            TransactionLine(
                transaction_id=txn.id,
                account_id=line.account_id,
                kassenbereich_id=line.kassenbereich_id,
                member_id=line.member_id,
                side=line.side,
                amount=to_decimal(line.amount),
                description=line.description,
                event_id=line.event_id,
            )
        )

    if tags:
        for name in tags:
            tag = db.scalar(select(Tag).where(Tag.name == name))
            if not tag:
                tag = Tag(name=name)
                db.add(tag)
                db.flush()
            txn.tags.append(tag)

    db.flush()
    _audit(db, user, AuditAction.CREATE, txn, description=f"Buchung #{txn.sequential_number} erstellt")
    return TransactionResult(transaction=txn, warnings=overdraw_warnings(db, lines, semester.id))


def overdraw_warnings(db: Session, lines: list[LineInput], semester_id: str | None) -> list[str]:
    """Return human-readable warnings for areas that would go negative."""
    deltas: dict[str, Decimal] = {}
    for line in lines:
        account = db.get(Account, line.account_id)
        if account and account.type in balances.BESTANDSKONTO_TYPES:
            delta = line.amount if line.side == Side.SOLL else -to_decimal(line.amount)
            deltas[line.kassenbereich_id] = deltas.get(line.kassenbereich_id, Decimal("0.0000")) + delta

    warnings: list[str] = []
    for kb_id, delta in deltas.items():
        if delta >= 0:
            continue
        kb = db.get(Kassenbereich, kb_id)
        current = balances.kassenbereich_balance(db, kb_id, semester_id)
        new_balance = current + delta
        if new_balance < 0:
            warnings.append(
                f"Durch diese Buchung wird der rechnerische Bestand der {kb.name} um "
                f"{abs(new_balance):.2f} € überzogen."
            )
    return warnings


def preview(db: Session, lines: list[LineInput], semester_id: str | None = None) -> dict:
    """Buchungsvorschau: Bestände vor/nach der Buchung + Überziehungswarnungen."""
    ids = {line.kassenbereich_id for line in lines}
    before = {kb_id: balances.kassenbereich_balance(db, kb_id, semester_id) for kb_id in ids}
    deltas: dict[str, Decimal] = {}
    for line in lines:
        account = db.get(Account, line.account_id)
        if account and account.type in balances.BESTANDSKONTO_TYPES:
            delta = to_decimal(line.amount) if line.side == Side.SOLL else -to_decimal(line.amount)
            deltas[line.kassenbereich_id] = deltas.get(line.kassenbereich_id, Decimal("0.0000")) + delta
    after = {kb_id: before.get(kb_id, Decimal("0.0000")) + deltas.get(kb_id, Decimal("0.0000")) for kb_id in ids}

    areas = []
    for kb_id in ids:
        kb = db.get(Kassenbereich, kb_id)
        areas.append(
            {
                "kassenbereich_id": kb_id,
                "name": kb.name if kb else kb_id,
                "before": before.get(kb_id, Decimal("0.0000")),
                "after": after.get(kb_id, Decimal("0.0000")),
                "overdrawn": after.get(kb_id, Decimal("0.0000")) < 0,
            }
        )
    return {"areas": areas, "warnings": overdraw_warnings(db, lines, semester_id)}


def stornate(db: Session, txn: Transaction, reason: str, user: User) -> Transaction:
    if txn.is_storno:
        raise ConflictError("Eine Stornobuchung kann nicht erneut storniert werden.")
    if txn.approval_status != ApprovalStatus.APPROVED:
        raise ConflictError("Nur freigegebene Buchungen können storniert werden.")
    already = db.scalar(
        select(Transaction).where(Transaction.storno_reference_id == txn.id)
    )
    if already:
        raise ConflictError("Buchung ist bereits storniert.")

    storno_lines = [
        LineInput(
            account_id=line.account_id,
            side=Side.HABEN if line.side == Side.SOLL else Side.SOLL,
            amount=line.amount,
            kassenbereich_id=line.kassenbereich_id,
            member_id=line.member_id,
            description=f"STORNO: {line.description or ''}".strip(),
            event_id=line.event_id,
        )
        for line in txn.lines
    ]
    result = create_transaction(
        db,
        date_=txn.date,
        description=f"STORNO: {txn.description} - {reason}",
        category=txn.category,
        lines=storno_lines,
        user=user,
        semester_id=txn.semester_id,
        tags=[tag.name for tag in txn.tags],
        is_internal_transfer=txn.is_internal_transfer,
        auto_approve=True,  # Storno wirkt sofort
    )
    storno = result.transaction
    storno.is_storno = True
    storno.storno_reference_id = txn.id
    db.flush()
    _audit(db, user, AuditAction.STORNO, storno, description=f"Buchung #{txn.sequential_number} storniert")
    return storno


def approve(db: Session, txn: Transaction, user: User, note: str | None = None) -> Transaction:
    """Gibt eine eingereichte Buchung frei – sie zählt ab jetzt in den Salden."""
    if txn.approval_status == ApprovalStatus.APPROVED:
        raise ConflictError("Buchung ist bereits freigegeben.")
    if txn.approval_status == ApprovalStatus.REJECTED:
        raise ConflictError("Buchung wurde abgelehnt und kann nicht freigegeben werden.")
    txn.approval_status = ApprovalStatus.APPROVED
    txn.approved_by_id = user.id
    txn.approved_at = utcnow()
    txn.review_note = note
    txn.is_locked = True
    db.flush()
    _audit(db, user, AuditAction.APPROVE, txn, description=f"Buchung #{txn.sequential_number} freigegeben")
    return txn


def reject(db: Session, txn: Transaction, user: User, note: str | None = None) -> Transaction:
    """Lehnt eine eingereichte Buchung ab – sie zählt nicht."""
    if txn.approval_status != ApprovalStatus.SUBMITTED:
        raise ConflictError("Nur eingereichte Buchungen können abgelehnt werden.")
    txn.approval_status = ApprovalStatus.REJECTED
    txn.approved_by_id = user.id
    txn.approved_at = utcnow()
    txn.review_note = note
    db.flush()
    _audit(db, user, AuditAction.APPROVE, txn, description=f"Buchung #{txn.sequential_number} abgelehnt")
    return txn


def lock(db: Session, txn: Transaction, user: User) -> Transaction:
    if txn.is_locked:
        raise ConflictError("Buchung ist bereits festgeschrieben.")
    txn.is_locked = True
    db.flush()
    _audit(db, user, AuditAction.UPDATE, txn, description=f"Buchung #{txn.sequential_number} festgeschrieben")
    return txn


def internal_transfer(
    db: Session,
    *,
    from_kassenbereich_id: str,
    to_kassenbereich_id: str,
    amount: Decimal,
    date_: date,
    user: User,
    note: str | None = None,
    semester_id: str | None = None,
) -> TransactionResult:
    if from_kassenbereich_id == to_kassenbereich_id:
        raise ValidationError("Quell- und Ziel-Kassenbereich müssen sich unterscheiden.")
    transfer_account = db.scalar(select(Account).where(Account.type == AccountType.TRANSFER))
    if not transfer_account:
        raise NotFoundError("Internes Umbuchungskonto fehlt (Seed ausführen).")
    from_kb = db.get(Kassenbereich, from_kassenbereich_id)
    to_kb = db.get(Kassenbereich, to_kassenbereich_id)
    if not from_kb or not to_kb:
        raise NotFoundError("Kassenbereich nicht gefunden.")
    lines = [
        LineInput(transfer_account.id, Side.HABEN, amount, from_kassenbereich_id,
                  description=f"Umbuchung an {to_kb.name}"),
        LineInput(transfer_account.id, Side.SOLL, amount, to_kassenbereich_id,
                  description=f"Umbuchung von {from_kb.name}"),
    ]
    return create_transaction(
        db,
        date_=date_,
        description=note or f"Interne Umbuchung {from_kb.name} → {to_kb.name}",
        category=TransactionCategory.MISC,
        lines=lines,
        user=user,
        semester_id=semester_id,
        is_internal_transfer=True,
    )


def _audit(db: Session, user: User, action: AuditAction, txn: Transaction, description: str | None = None):
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            action=action,
            entity_type="Transaction",
            entity_id=txn.id,
            description=description,
        )
    )
