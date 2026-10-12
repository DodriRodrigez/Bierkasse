from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import (
    BOOKING_APPROVE,
    BOOKING_CREATE,
    BOOKING_LOCK,
    BOOKING_READ,
    BOOKING_STORNO,
)
from app.database import get_db
from app.models.entities import Account, Transaction, TransactionLine, transaction_tags, User
from app.models.enums import ApprovalStatus, TransactionCategory
from app.schemas.accounting import (
    ApprovalRequest,
    PreviewRequest,
    PreviewResponse,
    StornoRequest,
    TransactionCreate,
    TransactionOut,
)
from app.services import accounting_service
from app.services.accounting_service import LineInput

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_line_inputs(payload) -> list[LineInput]:
    return [
        LineInput(
            account_id=line.account_id,
            side=line.side,
            amount=line.amount,
            kassenbereich_id=line.kassenbereich_id,
            member_id=line.member_id,
            description=line.description,
            event_id=line.event_id,
        )
        for line in payload.lines
    ]


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    response: Response,
    semester_id: str | None = None,
    category: TransactionCategory | None = None,
    approval_status: ApprovalStatus | None = None,
    account_id: str | None = None,
    kassenbereich_id: str | None = None,
    tag_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(BOOKING_READ)),
):
    stmt = select(Transaction).options(selectinload(Transaction.lines), selectinload(Transaction.tags))
    count_stmt = select(func.count(Transaction.id.distinct()))

    if approval_status:
        stmt = stmt.where(Transaction.approval_status == approval_status)
        count_stmt = count_stmt.where(Transaction.approval_status == approval_status)
    if kassenbereich_id:
        stmt = stmt.join(TransactionLine).where(TransactionLine.kassenbereich_id == kassenbereich_id)
        count_stmt = count_stmt.join(TransactionLine).where(TransactionLine.kassenbereich_id == kassenbereich_id)
    if account_id:
        stmt = stmt.join(TransactionLine).where(TransactionLine.account_id == account_id)
        count_stmt = count_stmt.join(TransactionLine).where(TransactionLine.account_id == account_id)
    if tag_id:
        stmt = stmt.join(transaction_tags).where(transaction_tags.c.tag_id == tag_id)
        count_stmt = count_stmt.join(transaction_tags).where(transaction_tags.c.tag_id == tag_id)
    if semester_id:
        stmt = stmt.where(Transaction.semester_id == semester_id)
        count_stmt = count_stmt.where(Transaction.semester_id == semester_id)
    if category:
        stmt = stmt.where(Transaction.category == category)
        count_stmt = count_stmt.where(Transaction.category == category)
    if date_from:
        stmt = stmt.where(Transaction.date >= date_from)
        count_stmt = count_stmt.where(Transaction.date >= date_from)
    if date_to:
        stmt = stmt.where(Transaction.date <= date_to)
        count_stmt = count_stmt.where(Transaction.date <= date_to)
    if search:
        stmt = stmt.where(Transaction.description.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(Transaction.description.ilike(f"%{search}%"))

    total = db.scalar(count_stmt) or 0
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Page"] = str(page)
    response.headers["X-Per-Page"] = str(per_page)

    stmt = stmt.order_by(Transaction.sequential_number.desc()).offset((page - 1) * per_page).limit(per_page)
    return list(db.scalars(stmt).unique())


@router.get("/my", response_model=list[TransactionOut])
def my_transactions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    account = user.account
    if not account:
        return []
    ids = select(TransactionLine.transaction_id).where(TransactionLine.account_id == account.id)
    stmt = (
        select(Transaction)
        .where(Transaction.id.in_(ids))
        .options(selectinload(Transaction.lines), selectinload(Transaction.tags))
        .order_by(Transaction.sequential_number.desc())
        .limit(50)
    )
    return list(db.scalars(stmt).unique())


@router.post("/preview", response_model=PreviewResponse)
def preview(payload: PreviewRequest, db: Session = Depends(get_db), _: User = Depends(require_permission(BOOKING_READ))):
    result = accounting_service.preview(db, _to_line_inputs(payload), payload.semester_id)
    return result


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(
    payload: TransactionCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(BOOKING_CREATE))
):
    result = accounting_service.create_transaction(
        db,
        date_=payload.date,
        description=payload.description,
        category=payload.category,
        lines=_to_line_inputs(payload),
        user=user,
        semester_id=payload.semester_id,
        tags=payload.tags,
        receipt_status=payload.receipt_status,
        lock=payload.lock,
    )
    txn = result.transaction
    response = TransactionOut.model_validate(txn)
    return txn


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(BOOKING_READ))):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise NotFoundError("Buchung nicht gefunden.")
    return txn


@router.post("/{transaction_id}/stornate", response_model=TransactionOut, status_code=201)
def storno(
    transaction_id: str,
    payload: StornoRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(BOOKING_STORNO)),
):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise NotFoundError("Buchung nicht gefunden.")
    return accounting_service.stornate(db, txn, payload.reason, user)


@router.post("/{transaction_id}/lock", response_model=TransactionOut)
def lock(transaction_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission(BOOKING_LOCK))):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise NotFoundError("Buchung nicht gefunden.")
    return accounting_service.lock(db, txn, user)


@router.get("/pending/list", response_model=list[TransactionOut])
def pending_transactions(db: Session = Depends(get_db), _: User = Depends(require_permission(BOOKING_APPROVE))):
    """Alle zur Freigabe eingereichten Buchungen."""
    stmt = (
        select(Transaction)
        .where(Transaction.approval_status == ApprovalStatus.SUBMITTED)
        .options(selectinload(Transaction.lines), selectinload(Transaction.tags))
        .order_by(Transaction.sequential_number.desc())
    )
    return list(db.scalars(stmt).unique())


@router.post("/{transaction_id}/approve", response_model=TransactionOut)
def approve(
    transaction_id: str,
    payload: ApprovalRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(BOOKING_APPROVE)),
):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise NotFoundError("Buchung nicht gefunden.")
    return accounting_service.approve(db, txn, user, payload.note if payload else None)


@router.post("/{transaction_id}/reject", response_model=TransactionOut)
def reject(
    transaction_id: str,
    payload: ApprovalRequest | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(BOOKING_APPROVE)),
):
    txn = db.get(Transaction, transaction_id)
    if not txn:
        raise NotFoundError("Buchung nicht gefunden.")
    return accounting_service.reject(db, txn, user, payload.note if payload else None)
