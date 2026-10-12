"""Idempotent database bootstrap / demo seed.

Run:  python -m app.seed
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.entities import Account, Beverage, Kassenbereich, Semester, Tag, User
from app.models.enums import (
    AccountType,
    MembershipStatus,
    RingColor,
    SemesterStatus,
    SemesterType,
    SystemRole,
)

KASSENBEREICHE = [
    ("CC-Kasse", "CC", 1),
    ("Bierkasse", "BIER", 2),
    ("allgemeiner Bereich", "ALLG", 3),
    ("Veranstaltungskasse", "VERANST", 4),
    ("Hausbereich", "HAUS", 5),
]

ACCOUNTS = [
    ("Onlinekonto", AccountType.GIRO),
    ("Barkonto CC", AccountType.CASH),
    ("Barkonto Bier", AccountType.CASH),
    ("Getränkeerlös", AccountType.REVENUE),
    ("Aufwand Getränkeeinkauf", AccountType.EXPENSE),
    ("Aufwand Bewirtung", AccountType.EXPENSE),
    ("Aufwand Auslagenerstattung", AccountType.EXPENSE),
    ("Aufwand Schwund", AccountType.EXPENSE),
    ("Verbindlichkeiten Lieferanten", AccountType.EXTERNAL),
    ("Eigenkapital", AccountType.CLEARING),
    ("Interne Umbuchung", AccountType.TRANSFER),
]

BEVERAGES = [
    ("St. Michaels Bräu", RingColor.RED, "0.70", "Bier"),
    ("Weizen", RingColor.YELLOW, "1.00", "Bier"),
    ("Mate", RingColor.YELLOW, "1.00", "Alkoholfrei"),
    ("Spezi", RingColor.RED, "0.70", "Alkoholfrei"),
]

TAGS = [("Stiftungsfest", "accent"), ("Konvent", "muted"), ("Couleurbesuch", "warn")]

MEMBERS = [
    ("Max", "Mustermann", "CB", SystemRole.BUCHHALTER),
    ("Anna", "Beispiel", "IaCB", SystemRole.MITGLIED),
    ("Lukas", "Muster", "CB", SystemRole.MITGLIED),
]


def _get_or_create(db: Session, model, defaults=None, **lookup):
    obj = db.scalar(select(model).filter_by(**lookup))
    if obj:
        return obj, False
    obj = model(**lookup, **(defaults or {}))
    db.add(obj)
    db.flush()
    return obj, True


def seed(db: Session) -> None:
    Base.metadata.create_all(engine)

    semester, _ = _get_or_create(
        db, Semester,
        name="WiSe 2026/27",
        defaults={"type": SemesterType.WINTER, "start_date": date(2026, 10, 1),
                  "end_date": date(2027, 3, 31), "status": SemesterStatus.ACTIVE},
    )

    for name, code, order in KASSENBEREICHE:
        _get_or_create(db, Kassenbereich, name=name, defaults={"code": code, "sort_order": order})

    for name, acc_type in ACCOUNTS:
        _get_or_create(db, Account, name=name, defaults={"type": acc_type})

    for name, color, price, category in BEVERAGES:
        _get_or_create(
            db, Beverage, name=name,
            defaults={"ring_color": color, "ring_price": Decimal(price), "category": category,
                      "semester_id": semester.id},
        )

    for name, color in TAGS:
        _get_or_create(db, Tag, name=name, defaults={"color": color})

    admin, created = _get_or_create(
        db, User, email=settings.bootstrap_admin_email,
        defaults={
            "password_hash": hash_password(settings.bootstrap_admin_password),
            "first_name": "Administrator", "last_name": "Bierkasse",
            "membership_status": MembershipStatus.AH, "system_role": SystemRole.ADMIN,
            "is_active": True,
        },
    )
    if created:
        db.add(Account(name=admin.full_name, type=AccountType.MEMBER, user_id=admin.id))
        db.flush()

    for first, last, status, role in MEMBERS:
        email = f"{first.lower()}.{last.lower()}@example.com"
        member, was_created = _get_or_create(
            db, User, email=email,
            defaults={
                "password_hash": hash_password(settings.bootstrap_member_password),
                "first_name": first, "last_name": last,
                "membership_status": MembershipStatus(status), "system_role": role,
                "is_active": True,
            },
        )
        if was_created:
            db.add(Account(name=member.full_name, type=AccountType.MEMBER, user_id=member.id))
            db.flush()

    db.commit()


def main() -> None:
    with SessionLocal() as db:
        seed(db)
    print("Seed abgeschlossen.")


if __name__ == "__main__":
    main()
