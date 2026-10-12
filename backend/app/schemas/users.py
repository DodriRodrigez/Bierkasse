from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import MembershipStatus, SystemRole
from app.schemas.common import Money, ORMModel


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str
    last_name: str
    membership_status: MembershipStatus = MembershipStatus.CB
    system_role: SystemRole = SystemRole.MITGLIED
    is_active: bool = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    iban: Optional[str] = None
    notes: Optional[str] = None
    membership_status: Optional[MembershipStatus] = None
    system_role: Optional[SystemRole] = None
    is_active: Optional[bool] = None


class UserOut(ORMModel):
    id: str
    email: str
    first_name: str
    last_name: str
    membership_status: MembershipStatus
    system_role: SystemRole
    phone: Optional[str] = None
    iban: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime] = None
    created_at: datetime


class MemberBalanceArea(BaseModel):
    kassenbereich_id: str
    name: str
    balance: Money


class MemberDashboard(BaseModel):
    user: UserOut
    total_balance: Money
    by_kassenbereich: list[MemberBalanceArea]
    recent_transactions: list["MemberTransactionRow"] = []


class MemberTransactionRow(BaseModel):
    id: str
    sequential_number: int
    date: str
    description: str
    amount: Money
    side: str


class SettlementEmailRequest(BaseModel):
    """Empfänger der Ausstands-Aufstellung (Standard: eigene E-Mail)."""

    to: Optional[EmailStr] = None
    semester_id: Optional[str] = None


class SettlementEmailResult(BaseModel):
    delivered: bool
    transport: str
    to: str
    from_: str = Field(alias="from")
    subject: str
    total: Money
    semester: str
    reason: Optional[str] = None
    path: Optional[str] = None

    model_config = {"populate_by_name": True}


MemberDashboard.model_rebuild()
