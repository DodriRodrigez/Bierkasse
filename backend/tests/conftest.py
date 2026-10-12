"""Pytest fixtures: isolated SQLite database and a seeded mini-world."""
from __future__ import annotations

import os
import tempfile

# Point the app at a throwaway database BEFORE any app module imports settings.
_TMP_DB = os.path.join(tempfile.gettempdir(), "bierkasse7_test.db")
os.environ.setdefault("BIERKASSE7_DATABASE_URL", f"sqlite:///{_TMP_DB}")

import pytest  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models.entities import Account, Kassenbereich, Semester, User  # noqa: E402
from app.models.enums import (  # noqa: E402
    AccountType,
    MembershipStatus,
    SemesterStatus,
    SemesterType,
    SystemRole,
)
from datetime import date  # noqa: E402


class World:
    """Convenience handles for the seeded mini-world."""

    def __init__(self, db: Session):
        self.db = db
        self.semester = db.scalar(select(Semester))
        self.kb = {kb.code: kb for kb in db.scalars(select(Kassenbereich))}
        self.acc = {a.name: a for a in db.scalars(select(Account))}

    def account(self, name: str) -> Account:
        return self.acc[name]


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture()
def world(db: Session) -> World:
    semester = Semester(
        name="WiSe 2026/27", type=SemesterType.WINTER,
        start_date=date(2026, 10, 1), end_date=date(2027, 3, 31), status=SemesterStatus.ACTIVE,
    )
    db.add(semester)
    for name, code, order in [("CC-Kasse", "CC", 1), ("Bierkasse", "BIER", 2), ("allgemeiner Bereich", "ALG", 3)]:
        db.add(Kassenbereich(name=name, code=code, sort_order=order))
    accounts = [
        ("Onlinekonto", AccountType.GIRO),
        ("Barkonto CC", AccountType.CASH),
        ("Getränkeerlös", AccountType.REVENUE),
        ("Aufwand", AccountType.EXPENSE),
        ("Eigenkapital", AccountType.CLEARING),
        ("Interne Umbuchung", AccountType.TRANSFER),
        ("Verbindlichkeiten", AccountType.EXTERNAL),
    ]
    for name, acc_type in accounts:
        db.add(Account(name=name, type=acc_type))

    admin = User(
        email="admin@testverbindung.de", password_hash=hash_password("admin123"),
        first_name="Admin", last_name="Test", membership_status=MembershipStatus.AH,
        system_role=SystemRole.ADMIN, is_active=True,
    )
    db.add(admin)
    member = User(
        email="cb@testverbindung.de", password_hash=hash_password("member123"),
        first_name="Cb", last_name="Member", membership_status=MembershipStatus.CB,
        system_role=SystemRole.MITGLIED, is_active=True,
    )
    db.add(member)
    db.flush()
    db.add(Account(name="Admin Test", type=AccountType.MEMBER, user_id=admin.id))
    db.add(Account(name="Cb Member", type=AccountType.MEMBER, user_id=member.id))
    db.flush()
    return World(db)
