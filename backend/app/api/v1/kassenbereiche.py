from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import KASSENBEREICH_MANAGE, TRANSFER_CREATE
from app.database import get_db
from app.models.entities import Kassenbereich, User
from app.schemas.accounting import (
    InternalTransferRequest,
    KassenbereichBalance,
    KassenbereichCreate,
    KassenbereichOut,
    KassenbereichUpdate,
    TransactionOut,
)
from app.services import accounting_service, balances

router = APIRouter(prefix="/kassenbereiche", tags=["kassenbereiche"])


@router.get("", response_model=list[KassenbereichOut])
def list_areas(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Kassenbereich).order_by(Kassenbereich.sort_order, Kassenbereich.name)))


@router.get("/balances", response_model=list[KassenbereichBalance])
def balances_view(
    semester_id: str | None = None, db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    areas = db.scalars(select(Kassenbereich).order_by(Kassenbereich.sort_order, Kassenbereich.name))
    return [
        KassenbereichBalance(
            id=kb.id, name=kb.name, code=kb.code, is_active=kb.is_active,
            balance=balances.kassenbereich_balance(db, kb.id, semester_id),
        )
        for kb in areas
    ]


@router.post("", response_model=KassenbereichOut, status_code=201)
def create_area(
    payload: KassenbereichCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(KASSENBEREICH_MANAGE))
):
    if db.scalar(select(Kassenbereich).where(Kassenbereich.code == payload.code)):
        raise ConflictError("Kassenbereich-Code existiert bereits.")
    kb = Kassenbereich(**payload.model_dump())
    db.add(kb)
    db.flush()
    return kb


@router.patch("/{area_id}", response_model=KassenbereichOut)
def update_area(
    area_id: str,
    payload: KassenbereichUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(KASSENBEREICH_MANAGE)),
):
    kb = db.get(Kassenbereich, area_id)
    if not kb:
        raise NotFoundError("Kassenbereich nicht gefunden.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(kb, key, value)
    db.flush()
    return kb


@router.post("/transfer", response_model=TransactionOut, status_code=201)
def transfer(
    payload: InternalTransferRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(TRANSFER_CREATE)),
):
    result = accounting_service.internal_transfer(
        db,
        from_kassenbereich_id=payload.from_kassenbereich_id,
        to_kassenbereich_id=payload.to_kassenbereich_id,
        amount=payload.amount,
        date_=payload.date,
        user=user,
        note=payload.note,
        semester_id=payload.semester_id,
    )
    return result.transaction
