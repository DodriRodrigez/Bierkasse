from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import DELIVERY_CREATE
from app.database import get_db
from app.models.entities import Beverage, Delivery, DeliveryItem, User
from app.schemas.features import DeliveryCreate, DeliveryOut
from app.services import posting_service

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("", response_model=list[DeliveryOut])
def list_deliveries(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Delivery).order_by(Delivery.date.desc())))


@router.post("", response_model=DeliveryOut, status_code=201)
def create_delivery(
    payload: DeliveryCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(DELIVERY_CREATE))
):
    delivery = Delivery(
        date=payload.date,
        supplier=payload.supplier,
        invoice_number=payload.invoice_number,
        kassenbereich_id=payload.kassenbereich_id,
        payment_account_id=payload.payment_account_id,
        semester_id=payload.semester_id,
        created_by_id=user.id,
    )
    db.add(delivery)
    db.flush()
    for item in payload.items:
        beverage = db.get(Beverage, item.beverage_id)
        if not beverage:
            raise NotFoundError("Getränk nicht gefunden.")
        db.add(
            DeliveryItem(
                delivery_id=delivery.id,
                beverage_id=item.beverage_id,
                crates=item.crates,
                single_bottles=item.single_bottles,
                purchase_price=item.purchase_price,
                deposit=item.deposit,
            )
        )
    db.flush()
    return delivery


@router.post("/{delivery_id}/post", response_model=DeliveryOut)
def post_delivery(delivery_id: str, db: Session = Depends(get_db), user: User = Depends(require_permission(DELIVERY_CREATE))):
    delivery = db.get(Delivery, delivery_id)
    if not delivery:
        raise NotFoundError("Lieferung nicht gefunden.")
    posting_service.post_delivery(db, delivery, user)
    return delivery
