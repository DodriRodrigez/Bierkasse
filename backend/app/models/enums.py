"""Domain enumerations."""
from __future__ import annotations

import enum


class MembershipStatus(str, enum.Enum):
    CB = "CB"
    IaCB = "IaCB"
    IdC = "IdC"
    F = "F"
    Spef = "Spef"
    FcK = "FcK"
    AH = "AH"
    AH_IdC = "AH-IdC"
    CK = "CK"
    EXT = "EXT"


class SystemRole(str, enum.Enum):
    ADMIN = "admin"
    SENIOR = "senior"
    BUCHHALTER = "buchhalter"
    ORGANISATOR = "organisator"
    MITGLIED = "mitglied"
    GAST = "gast"


class SemesterType(str, enum.Enum):
    WINTER = "winter"
    SUMMER = "summer"


class SemesterStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    REOPENED = "reopened"


class AccountType(str, enum.Enum):
    """Buchhalterische Kontoart.

    giro/cash/cc are real payment accounts ("Zahlungskonten"); member, external,
    revenue, expense and clearing are bookkeeping accounts.
    """

    GIRO = "giro"
    CASH = "cash"
    CC = "cc"
    MEMBER = "member"
    EXTERNAL = "external"
    REVENUE = "revenue"
    EXPENSE = "expense"
    CLEARING = "clearing"
    TRANSFER = "transfer"  # Kassenbereichs-Umbuchung


PAYMENT_ACCOUNT_TYPES = {AccountType.GIRO, AccountType.CASH, AccountType.CC}


class TransactionCategory(str, enum.Enum):
    RB = "RB"      # Ringbrett
    CB = "CB"      # Couleurbesuch / Veranstaltung
    VS = "VS"      # Verkauf/Sonstiges
    BL = "BL"      # Beleglieferung
    AB = "AB"      # Abbuchung
    MISC = "MISC"


class ReceiptStatus(str, enum.Enum):
    NN = "NN"  # no receipt needed
    BU = "BU"  # receipt present
    UN = "UN"  # receipt missing


class Side(str, enum.Enum):
    SOLL = "SOLL"
    HABEN = "HABEN"


class RingColor(str, enum.Enum):
    RED = "red"
    YELLOW = "yellow"


class EventType(str, enum.Enum):
    PUBLIC = "public"
    PRIVATE = "private"


class PayerType(str, enum.Enum):
    CC_CASH = "cc_cash"
    MEMBER = "member"


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PAID = "paid"


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    STORNO = "STORNO"
    APPROVE = "APPROVE"
    LOGIN = "LOGIN"


class NotificationType(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"


class ApprovalStatus(str, enum.Enum):
    """Freigabe-Status einer Buchung.

    ``SUBMITTED`` – zur Freigabe eingereicht, noch nicht in den Salden.
    ``APPROVED``  – freigegeben/gebucht (zählt in Beständen, unveränderlich).
    ``REJECTED``  – abgelehnt, zählt nicht.
    """

    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"
