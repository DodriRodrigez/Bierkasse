from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import REFUND_APPROVE, REFUND_CREATE, READ_ALL
from app.core.permissions import has_permission
from app.database import get_db
from app.models.base import utcnow
from app.models.entities import ExpenseRefundRequest, User
from app.models.enums import RefundStatus
from app.schemas.features import RefundCreate, RefundOut
from app.services import posting_service

router = APIRouter(prefix="/refunds", tags=["refunds"])


@router.get("", response_model=list[RefundOut])
def list_refunds(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(ExpenseRefundRequest)
    if not has_permission(user.system_role, READ_ALL):
        stmt = stmt.where(ExpenseRefundRequest.applicant_id == user.id)
    return list(db.scalars(stmt.order_by(ExpenseRefundRequest.date.desc())))


@router.post("", response_model=RefundOut, status_code=201)
def create_refund(payload: RefundCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(REFUND_CREATE))):
    refund = ExpenseRefundRequest(
        applicant_id=user.id,
        date=payload.date,
        amount=payload.amount,
        description=payload.description,
        kassenbereich_id=payload.kassenbereich_id,
        receipt_file=payload.receipt_file,
        status=RefundStatus.PENDING,
    )
    db.add(refund)
    db.flush()
    return refund


@router.post("/{refund_id}/approve", response_model=RefundOut)
def approve(refund_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission(REFUND_APPROVE))):
    refund = db.get(ExpenseRefundRequest, refund_id)
    if not refund:
        raise NotFoundError("Antrag nicht gefunden.")
    refund.status = RefundStatus.APPROVED
    refund.approved_by_id = user.id
    refund.approved_at = utcnow()
    db.flush()
    posting_service.post_refund(db, refund, user)
    return refund


@router.post("/{refund_id}/reject", response_model=RefundOut)
def reject(refund_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission(REFUND_APPROVE))):
    refund = db.get(ExpenseRefundRequest, refund_id)
    if not refund:
        raise NotFoundError("Antrag nicht gefunden.")
    refund.status = RefundStatus.REJECTED
    refund.approved_by_id = user.id
    refund.approved_at = utcnow()
    db.flush()
    return refund
