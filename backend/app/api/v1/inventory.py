from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import INVENTORY_CREATE
from app.database import get_db
from app.models.entities import Beverage, Delivery, DeliveryItem, Inventory, InventoryItem, User
from app.schemas.features import InventoryCreate, InventoryOut

router = APIRouter(prefix="/inventories", tags=["inventory"])


@router.get("", response_model=list[InventoryOut])
def list_inventories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Inventory).order_by(Inventory.date.desc())))


@router.post("", response_model=InventoryOut, status_code=201)
def create_inventory(
    payload: InventoryCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(INVENTORY_CREATE))
):
    inventory = Inventory(
        date=payload.date, counted_by_id=user.id, semester_id=payload.semester_id, notes=payload.notes
    )
    db.add(inventory)
    db.flush()
    for item in payload.items:
        db.add(
            InventoryItem(
                inventory_id=inventory.id,
                beverage_id=item.beverage_id,
                crates=item.crates,
                single_bottles=item.single_bottles,
            )
        )
    db.flush()
    return inventory


@router.get("/{inventory_id}/comparison")
def comparison(inventory_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    inventory = db.get(Inventory, inventory_id)
    if not inventory:
        raise NotFoundError("Inventur nicht gefunden.")

    counted: dict[str, int] = {}
    for item in inventory.items:
        beverage = db.get(Beverage, item.beverage_id)
        per_crate = beverage.bottles_per_crate if beverage else 20
        counted[item.beverage_id] = counted.get(item.beverage_id, 0) + item.crates * per_crate + item.single_bottles

    delivered: dict[str, int] = {}
    for delivery in db.scalars(select(Delivery)):
        for ditem in delivery.items:
            beverage = db.get(Beverage, ditem.beverage_id)
            per_crate = beverage.bottles_per_crate if beverage else 20
            delivered[ditem.beverage_id] = delivered.get(ditem.beverage_id, 0) + ditem.crates * per_crate + ditem.single_bottles

    rows = []
    for beverage in db.scalars(select(Beverage)):
        ist = counted.get(beverage.id, 0)
        soll = delivered.get(beverage.id, 0)
        diff = ist - soll
        rows.append(
            {
                "beverage_id": beverage.id,
                "name": beverage.name,
                "delivered": soll,
                "counted": ist,
                "difference": diff,
                "deviation_percent": float(Decimal(abs(diff)) / soll * 100) if soll else 0.0,
            }
        )
    return {"inventory_id": inventory_id, "rows": rows}
