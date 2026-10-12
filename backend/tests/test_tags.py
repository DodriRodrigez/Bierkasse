"""Tags: CC-Kasse bookings can be tagged for event assignment."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select

from app.models.entities import Tag, User
from app.models.enums import Side, SystemRole, TransactionCategory
from app.services import accounting_service
from app.services.accounting_service import LineInput

D = date(2026, 11, 1)


def _admin(db) -> User:
    return db.scalar(select(User).where(User.system_role == SystemRole.ADMIN))


def test_booking_can_carry_tags(db, world):
    result = accounting_service.create_transaction(
        db, date_=D, description="CC-Ausgabe Stiftungsfest", category=TransactionCategory.CB,
        lines=[
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("120"), world.kb["CC"].id),
            LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("120"), world.kb["CC"].id),
        ],
        user=_admin(db), semester_id=world.semester.id,
        tags=["Stiftungsfest", "Couleurbesuch"],
    )
    db.flush()
    names = {t.name for t in result.transaction.tags}
    assert names == {"Stiftungsfest", "Couleurbesuch"}
    # tags are reusable entities
    assert db.scalar(select(Tag).where(Tag.name == "Stiftungsfest")) is not None


def test_booking_can_be_filtered_by_tag(db, world):
    from app.models.entities import Transaction, transaction_tags

    result = accounting_service.create_transaction(
        db, date_=D, description="Relevant", category=TransactionCategory.CB,
        lines=[
            LineInput(world.account("Aufwand").id, Side.SOLL, Decimal("10"), world.kb["CC"].id),
            LineInput(world.account("Onlinekonto").id, Side.HABEN, Decimal("10"), world.kb["CC"].id),
        ],
        user=_admin(db), semester_id=world.semester.id, tags=["Konvent"],
    )
    db.flush()
    tag = db.scalar(select(Tag).where(Tag.name == "Konvent"))
    found = db.scalars(
        select(Transaction).join(transaction_tags).where(transaction_tags.c.tag_id == tag.id)
    ).all()
    assert result.transaction.id in {t.id for t in found}
