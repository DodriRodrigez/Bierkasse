from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import (
    EventType,
    PayerType,
    RefundStatus,
    RingColor,
    SemesterStatus,
    SemesterType,
)
from app.schemas.accounting import TagOut
from app.schemas.common import Money, ORMModel


class SemesterCreate(BaseModel):
    name: str
    type: SemesterType
    start_date: date
    end_date: date


class SemesterOut(ORMModel):
    id: str
    name: str
    type: SemesterType
    start_date: date
    end_date: date
    status: SemesterStatus


class BeverageCreate(BaseModel):
    name: str
    ring_color: RingColor
    ring_price: Money
    bottles_per_crate: int = 20
    category: str = "Bier"
    deposit_per_bottle: Money = 0


class BeverageOut(ORMModel):
    id: str
    name: str
    ring_color: RingColor
    ring_price: Money
    bottles_per_crate: int
    category: str
    deposit_per_bottle: Money
    is_active: bool


class DeliveryItemIn(BaseModel):
    beverage_id: str
    crates: int = 0
    single_bottles: int = 0
    purchase_price: Money = 0
    deposit: Money = 0


class DeliveryCreate(BaseModel):
    date: date
    supplier: str
    invoice_number: Optional[str] = None
    kassenbereich_id: str
    payment_account_id: Optional[str] = None
    semester_id: Optional[str] = None
    items: list[DeliveryItemIn] = Field(min_length=1)


class DeliveryOut(ORMModel):
    id: str
    date: date
    supplier: str
    invoice_number: Optional[str] = None
    kassenbereich_id: Optional[str] = None
    is_posted: bool
    transaction_id: Optional[str] = None


class RingbrettEntryIn(BaseModel):
    user_id: str
    red_rings: int = 0
    yellow_rings: int = 0


class RingbrettCreate(BaseModel):
    date: date
    kassenbereich_id: str
    semester_id: Optional[str] = None
    notes: Optional[str] = None
    entries: list[RingbrettEntryIn] = Field(min_length=1)


class RingbrettEntryOut(ORMModel):
    id: str
    user_id: str
    red_rings: int
    yellow_rings: int


class RingbrettOut(ORMModel):
    id: str
    date: date
    kassenbereich_id: str
    zaehlungsnummer: int
    status: str
    notes: Optional[str] = None
    transaction_id: Optional[str] = None
    entries: list[RingbrettEntryOut] = []


class SelfRingEntryIn(BaseModel):
    """Eigene Ringe erfassen – nur für die angemeldete Person selbst."""

    date: date
    red_rings: int = Field(default=0, ge=0)
    yellow_rings: int = Field(default=0, ge=0)
    kassenbereich_id: Optional[str] = None
    notes: Optional[str] = None


class EventCreate(BaseModel):
    date: date
    name: str
    type: EventType
    payer_type: PayerType
    payer_user_id: Optional[str] = None
    signature: Optional[str] = None
    red_glasses: int = 0
    yellow_glasses: int = 0
    donation: Money = 0
    kassenbereich_id: str
    semester_id: Optional[str] = None
    tags: list[str] = []
    post: bool = True


class EventOut(ORMModel):
    id: str
    date: date
    name: str
    type: EventType
    payer_type: PayerType
    payer_user_id: Optional[str] = None
    red_glasses: int
    yellow_glasses: int
    donation: Money
    kassenbereich_id: str
    is_posted: bool
    transaction_id: Optional[str] = None
    tags: list[TagOut] = []


class InventoryItemIn(BaseModel):
    beverage_id: str
    crates: int = 0
    single_bottles: int = 0


class InventoryCreate(BaseModel):
    date: date
    semester_id: Optional[str] = None
    notes: Optional[str] = None
    items: list[InventoryItemIn] = Field(min_length=1)


class InventoryItemOut(ORMModel):
    id: str
    beverage_id: str
    crates: int
    single_bottles: int


class InventoryOut(ORMModel):
    id: str
    date: date
    status: str
    notes: Optional[str] = None
    items: list[InventoryItemOut] = []


class RefundCreate(BaseModel):
    date: date
    amount: Money
    description: str
    kassenbereich_id: str
    receipt_file: Optional[str] = None


class RefundOut(ORMModel):
    id: str
    date: date
    amount: Money
    description: str
    kassenbereich_id: str
    status: RefundStatus
    transaction_id: Optional[str] = None


class AuditLogOut(ORMModel):
    id: str
    user_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    description: Optional[str] = None
    created_at: datetime


class NotificationOut(ORMModel):
    id: str
    subject: str
    body: str
    is_read: bool
    created_at: datetime
