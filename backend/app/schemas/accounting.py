from __future__ import annotations

import datetime as dt
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import AccountType, ApprovalStatus, ReceiptStatus, Side, TransactionCategory
from app.schemas.common import Money, ORMModel


# --- Kassenbereich --------------------------------------------------------
class KassenbereichCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(min_length=1, max_length=40)
    description: Optional[str] = None
    sort_order: int = 0


class KassenbereichUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class KassenbereichOut(ORMModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    is_active: bool
    sort_order: int


class KassenbereichBalance(BaseModel):
    id: str
    name: str
    code: str
    is_active: bool
    balance: Money


# --- Tags -----------------------------------------------------------------
class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = "accent"
    description: Optional[str] = None


class TagOut(ORMModel):
    id: str
    name: str
    color: str
    description: Optional[str] = None


# --- Account --------------------------------------------------------------
class AccountCreate(BaseModel):
    name: str
    type: AccountType
    is_active: bool = True


class AccountOut(ORMModel):
    id: str
    name: str
    type: AccountType
    user_id: Optional[str] = None
    is_active: bool


class AccountBalanceOut(BaseModel):
    account: AccountOut
    balance: Money


# --- Transactions ---------------------------------------------------------
class LineIn(BaseModel):
    account_id: str
    side: Side
    amount: Money
    kassenbereich_id: str
    member_id: Optional[str] = None
    description: Optional[str] = None
    event_id: Optional[str] = None


class TransactionCreate(BaseModel):
    date: date
    description: str = Field(min_length=1, max_length=500)
    category: TransactionCategory
    lines: list[LineIn] = Field(min_length=2)
    semester_id: Optional[str] = None
    tags: list[str] = []
    receipt_status: Optional[ReceiptStatus] = None
    lock: bool = False


class LineOut(ORMModel):
    id: str
    account_id: str
    kassenbereich_id: str
    member_id: Optional[str] = None
    side: Side
    amount: Money
    description: Optional[str] = None


class TransactionOut(ORMModel):
    id: str
    sequential_number: int
    date: date
    description: str
    category: TransactionCategory
    receipt_status: Optional[ReceiptStatus] = None
    is_storno: bool
    is_locked: bool
    is_internal_transfer: bool
    approval_status: ApprovalStatus
    approved_at: Optional[datetime] = None
    approved_by_id: Optional[str] = None
    review_note: Optional[str] = None
    created_by_id: str
    notes: Optional[str] = None
    storno_reference_id: Optional[str] = None
    created_at: datetime
    lines: list[LineOut] = []
    tags: list[TagOut] = []


class ApprovalRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=300)


class StornoRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class PreviewRequest(BaseModel):
    # dt.date statt date: der Feldname "date" würde den gleichnamigen Typ
    # überschatten (Pydantic löst die Annotation sonst zu None auf).
    date: Optional[dt.date] = None
    lines: list[LineIn] = Field(min_length=2)
    semester_id: Optional[str] = None


class PreviewArea(BaseModel):
    kassenbereich_id: str
    name: str
    before: Money
    after: Money
    overdrawn: bool


class PreviewResponse(BaseModel):
    areas: list[PreviewArea]
    warnings: list[str]


class InternalTransferRequest(BaseModel):
    from_kassenbereich_id: str
    to_kassenbereich_id: str
    amount: Money
    date: date
    note: Optional[str] = None
    semester_id: Optional[str] = None
