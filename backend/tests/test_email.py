"""Verrechnungs-E-Mail: Aufstellung der Ausstände und Versand (Outbox-Fallback)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.models.entities import User
from app.models.enums import Side, SystemRole, TransactionCategory
from app.services import accounting_service, email_service
from app.services.accounting_service import LineInput

D = date(2026, 11, 1)


def _admin(db) -> User:
    return db.scalar(select(User).where(User.system_role == SystemRole.ADMIN))


def test_settlement_lists_balances_per_kassenbereich(db, world):
    member = db.scalar(select(User).where(User.system_role == SystemRole.MITGLIED))
    revenue = world.account("Getränkeerlös")
    accounting_service.create_transaction(
        db, date_=D, description="Bierkasse", category=TransactionCategory.RB,
        lines=[
            LineInput(member.account.id, Side.SOLL, Decimal("25.90"), world.kb["BIER"].id, member_id=member.id),
            LineInput(revenue.id, Side.HABEN, Decimal("25.90"), world.kb["BIER"].id),
        ],
        user=_admin(db), semester_id=world.semester.id,
    )
    accounting_service.create_transaction(
        db, date_=D, description="CC-Kasse", category=TransactionCategory.CB,
        lines=[
            LineInput(member.account.id, Side.SOLL, Decimal("12.00"), world.kb["CC"].id, member_id=member.id),
            LineInput(revenue.id, Side.HABEN, Decimal("12.00"), world.kb["CC"].id),
        ],
        user=_admin(db), semester_id=world.semester.id,
    )
    db.flush()

    rendered = email_service.render_settlement_email(db, member)
    assert rendered["total"] == Decimal("37.9000")
    names = {row["name"] for row in email_service.settlement_context(db, member)["rows"]}
    assert names == {"Bierkasse", "CC-Kasse"}
    assert "37,90" in rendered["text"]


def test_send_email_without_smtp_writes_outbox(db, world, tmp_path: Path, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", None)
    monkeypatch.setattr(settings, "outbox_dir", str(tmp_path))
    member = db.scalar(select(User).where(User.system_role == SystemRole.MITGLIED))

    result = email_service.send_settlement_email(db, member, to="empfaenger@example.com")

    assert result["delivered"] is False
    assert result["transport"] == "outbox"
    assert result["to"] == "empfaenger@example.com"
    written = list(tmp_path.glob("*.eml"))
    assert len(written) == 1
    content = written[0].read_bytes()
    assert b"To: empfaenger@example.com" in content
