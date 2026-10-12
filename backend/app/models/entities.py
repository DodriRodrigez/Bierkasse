"""ORM entities for Bierkasse7.

Design notes
------------
* Primary keys are portable UUID strings (``String(36)``) so the same schema runs
  on SQLite and PostgreSQL.
* Money columns use :class:`MoneyType` (exact Decimal, never float).
* Every :class:`TransactionLine` carries a mandatory ``kassenbereich_id`` — the
  accounting dimension required by the Kassenbereich specification.  ``Tag`` is
  a separate, free-form dimension used for search/filtering and for assigning
  CC-Kasse bookings to events.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.money import MoneyType
from app.models.base import Base, TimestampMixin, new_uuid, utcnow
from app.models.enums import (
    AccountType,
    ApprovalStatus,
    AuditAction,
    EventType,
    MembershipStatus,
    NotificationType,
    PayerType,
    ReceiptStatus,
    RefundStatus,
    RingColor,
    SemesterStatus,
    SemesterType,
    Side,
    SystemRole,
    TransactionCategory,
)


def enum_col(enum_cls: type[enum.Enum], length: int = 40):
    """Portable enum column storing the enum *value*."""
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=length,
        values_callable=lambda e: [m.value for m in e],
    )


# --------------------------------------------------------------------------
# Association tables (many-to-many)
# --------------------------------------------------------------------------
transaction_tags = Table(
    "transaction_tags",
    Base.metadata,
    Column("transaction_id", String(36), ForeignKey("transactions.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

event_tags = Table(
    "event_tags",
    Base.metadata,
    Column("event_id", String(36), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


# --------------------------------------------------------------------------
# Identity & periods
# --------------------------------------------------------------------------
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    membership_status: Mapped[MembershipStatus] = mapped_column(
        enum_col(MembershipStatus), nullable=False, default=MembershipStatus.CB
    )
    system_role: Mapped[SystemRole] = mapped_column(
        enum_col(SystemRole), nullable=False, default=SystemRole.MITGLIED
    )
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    iban: Mapped[Optional[str]] = mapped_column(String(34))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)

    account: Mapped[Optional["Account"]] = relationship(
        "Account", back_populates="user", uselist=False, foreign_keys="Account.user_id"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Semester(Base, TimestampMixin):
    __tablename__ = "semesters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    type: Mapped[SemesterType] = mapped_column(enum_col(SemesterType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[SemesterStatus] = mapped_column(
        enum_col(SemesterStatus), nullable=False, default=SemesterStatus.ACTIVE
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    closed_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))


# --------------------------------------------------------------------------
# Accounts, Kassenbereiche, Tags
# --------------------------------------------------------------------------
class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[AccountType] = mapped_column(enum_col(AccountType), nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id"), unique=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped[Optional["User"]] = relationship(
        "User", back_populates="account", foreign_keys=[user_id]
    )
    lines: Mapped[list["TransactionLine"]] = relationship("TransactionLine", back_populates="account")
    balances: Mapped[list["AccountBalance"]] = relationship("AccountBalance", back_populates="account")

    @property
    def is_payment_account(self) -> bool:
        return self.type in (AccountType.GIRO, AccountType.CASH, AccountType.CC)


class Kassenbereich(Base, TimestampMixin):
    """Internal cash area — a mandatory, bookkeeping-relevant dimension."""

    __tablename__ = "kassenbereiche"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(MoneyType, default=0, nullable=False)


class Tag(Base, TimestampMixin):
    """Free-form label for search/filtering and event assignment (e.g. CC-Kasse)."""

    __tablename__ = "tags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="accent", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300))


# --------------------------------------------------------------------------
# Bookkeeping
# --------------------------------------------------------------------------
class Transaction(Base, TimestampMixin):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    sequential_number: Mapped[int] = mapped_column(Integer, autoincrement=True, unique=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    category: Mapped[TransactionCategory] = mapped_column(enum_col(TransactionCategory), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False, index=True)
    receipt_file: Mapped[Optional[str]] = mapped_column(String(500))
    receipt_status: Mapped[Optional[ReceiptStatus]] = mapped_column(enum_col(ReceiptStatus))
    migration_source: Mapped[Optional[str]] = mapped_column(String(100))
    is_storno: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_internal_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Freigabe-Workflow: eingereichte Buchungen zählen erst nach Freigabe.
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_col(ApprovalStatus), default=ApprovalStatus.APPROVED, nullable=False, index=True
    )
    approved_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    review_note: Mapped[Optional[str]] = mapped_column(String(300))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    storno_reference_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    semester: Mapped["Semester"] = relationship("Semester")
    created_by: Mapped["User"] = relationship("User", foreign_keys=[created_by_id])
    lines: Mapped[list["TransactionLine"]] = relationship(
        "TransactionLine", back_populates="transaction", cascade="all, delete-orphan",
        foreign_keys="TransactionLine.transaction_id",
    )
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=transaction_tags, lazy="selectin")


class TransactionLine(Base, TimestampMixin):
    __tablename__ = "transaction_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    transaction_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transactions.id"), nullable=False, index=True
    )
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False, index=True)
    kassenbereich_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("kassenbereiche.id"), nullable=False, index=True
    )
    member_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    side: Mapped[Side] = mapped_column(enum_col(Side), nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyType, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(300))
    event_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("events.id"))

    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="lines", foreign_keys=[transaction_id]
    )
    account: Mapped["Account"] = relationship("Account", back_populates="lines")
    kassenbereich: Mapped["Kassenbereich"] = relationship("Kassenbereich")
    member: Mapped[Optional["User"]] = relationship("User", foreign_keys=[member_id])


class AccountBalance(Base, TimestampMixin):
    __tablename__ = "account_balances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    account_id: Mapped[str] = mapped_column(String(36), ForeignKey("accounts.id"), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False)
    opening_balance: Mapped[Decimal] = mapped_column(MoneyType, default=0, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="balances")
    semester: Mapped["Semester"] = relationship("Semester")

    __table_args__ = (UniqueConstraint("account_id", "semester_id", name="uq_account_semester"),)


# --------------------------------------------------------------------------
# Beverages & deliveries
# --------------------------------------------------------------------------
class Beverage(Base, TimestampMixin):
    __tablename__ = "beverages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    ring_color: Mapped[RingColor] = mapped_column(enum_col(RingColor), nullable=False)
    ring_price: Mapped[Decimal] = mapped_column(MoneyType, nullable=False)
    bottles_per_crate: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="Bier", nullable=False)
    deposit_per_bottle: Mapped[Decimal] = mapped_column(MoneyType, default=Decimal("0.08"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    semester_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("semesters.id"))


class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    supplier: Mapped[str] = mapped_column(String(200), nullable=False)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100))
    invoice_file: Mapped[Optional[str]] = mapped_column(String(500))
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False)
    kassenbereich_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("kassenbereiche.id"))
    payment_account_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("accounts.id"))
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    items: Mapped[list["DeliveryItem"]] = relationship(
        "DeliveryItem", back_populates="delivery", cascade="all, delete-orphan"
    )


class DeliveryItem(Base, TimestampMixin):
    __tablename__ = "delivery_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    delivery_id: Mapped[str] = mapped_column(String(36), ForeignKey("deliveries.id"), nullable=False)
    beverage_id: Mapped[str] = mapped_column(String(36), ForeignKey("beverages.id"), nullable=False)
    crates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    single_bottles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    purchase_price: Mapped[Decimal] = mapped_column(MoneyType, default=0, nullable=False)
    deposit: Mapped[Decimal] = mapped_column(MoneyType, default=0, nullable=False)

    delivery: Mapped["Delivery"] = relationship("Delivery", back_populates="items")
    beverage: Mapped["Beverage"] = relationship("Beverage")

    @property
    def bottles_total(self) -> int:
        return self.crates * (self.beverage.bottles_per_crate if self.beverage else 20) + self.single_bottles


# --------------------------------------------------------------------------
# Ringbrett & events
# --------------------------------------------------------------------------
class RingbrettSession(Base, TimestampMixin):
    __tablename__ = "ringbrett_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    counted_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False)
    kassenbereich_id: Mapped[str] = mapped_column(String(36), ForeignKey("kassenbereiche.id"), nullable=False)
    zaehlungsnummer: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))

    entries: Mapped[list["RingbrettEntry"]] = relationship(
        "RingbrettEntry", back_populates="session", cascade="all, delete-orphan"
    )


class RingbrettEntry(Base, TimestampMixin):
    __tablename__ = "ringbrett_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("ringbrett_sessions.id"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    red_rings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_rings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    session: Mapped["RingbrettSession"] = relationship("RingbrettSession", back_populates="entries")
    user: Mapped["User"] = relationship("User")

    __table_args__ = (UniqueConstraint("session_id", "user_id", name="uq_session_user"),)


class Event(Base, TimestampMixin):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[EventType] = mapped_column(enum_col(EventType), nullable=False)
    organizer_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    signature: Mapped[Optional[str]] = mapped_column(String(100))
    payer_type: Mapped[PayerType] = mapped_column(enum_col(PayerType), nullable=False)
    payer_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    red_glasses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yellow_glasses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    donation: Mapped[Decimal] = mapped_column(MoneyType, default=0, nullable=False)
    kassenbereich_id: Mapped[str] = mapped_column(String(36), ForeignKey("kassenbereiche.id"), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False)
    is_posted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))
    created_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    organizer: Mapped["User"] = relationship("User", foreign_keys=[organizer_id])
    payer_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[payer_user_id])
    tags: Mapped[list["Tag"]] = relationship("Tag", secondary=event_tags, lazy="selectin")


# --------------------------------------------------------------------------
# Inventory, refunds, audit, notifications
# --------------------------------------------------------------------------
class Inventory(Base, TimestampMixin):
    __tablename__ = "inventories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    counted_by_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    semester_id: Mapped[str] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))

    items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="inventory", cascade="all, delete-orphan"
    )


class InventoryItem(Base, TimestampMixin):
    __tablename__ = "inventory_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    inventory_id: Mapped[str] = mapped_column(String(36), ForeignKey("inventories.id"), nullable=False)
    beverage_id: Mapped[str] = mapped_column(String(36), ForeignKey("beverages.id"), nullable=False)
    crates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    single_bottles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    inventory: Mapped["Inventory"] = relationship("Inventory", back_populates="items")
    beverage: Mapped["Beverage"] = relationship("Beverage")


class ExpenseRefundRequest(Base, TimestampMixin):
    __tablename__ = "expense_refund_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    applicant_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(MoneyType, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    kassenbereich_id: Mapped[str] = mapped_column(String(36), ForeignKey("kassenbereiche.id"), nullable=False)
    receipt_file: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[RefundStatus] = mapped_column(
        enum_col(RefundStatus), nullable=False, default=RefundStatus.PENDING
    )
    approved_by_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    transaction_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transactions.id"))

    applicant: Mapped["User"] = relationship("User", foreign_keys=[applicant_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"))
    action: Mapped[AuditAction] = mapped_column(enum_col(AuditAction), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    old_values: Mapped[Optional[dict]] = mapped_column(JSON)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped[Optional["User"]] = relationship("User")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[NotificationType] = mapped_column(
        enum_col(NotificationType), nullable=False, default=NotificationType.IN_APP
    )
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    user: Mapped["User"] = relationship("User")
