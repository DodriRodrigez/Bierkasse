from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import DELIVERY_CREATE
from app.database import get_db
from app.models.entities import Beverage, User
from app.schemas.features import BeverageCreate, BeverageOut
from app.services import posting_service

router = APIRouter(prefix="/beverages", tags=["beverages"])


@router.get("", response_model=list[BeverageOut])
def list_beverages(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Beverage).where(Beverage.is_active.is_(True)).order_by(Beverage.category, Beverage.name)))


@router.post("", response_model=BeverageOut, status_code=201)
def create_beverage(
    payload: BeverageCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(DELIVERY_CREATE))
):
    beverage = Beverage(**payload.model_dump())
    db.add(beverage)
    db.flush()
    return beverage


@router.get("/ring-prices")
def ring_prices(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    prices = posting_service.ring_price_summary(db)
    return {"red": prices["red"], "yellow": prices["yellow"]}
