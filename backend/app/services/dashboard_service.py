"""Dashboard aggregations: liquidity view, area-balance view, control equation."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Account, Kassenbereich, Transaction, TransactionLine
from app.models.enums import AccountType, SemesterStatus, Side
from app.services import balances


def _active_semester_id(db: Session) -> str | None:
    from app.models.entities import Semester

    semester = db.scalar(select(Semester).where(Semester.status == SemesterStatus.ACTIVE))
    return semester.id if semester else None


def liquidity_view(db: Session, semester_id: str | None = None) -> dict:
    semester_id = semester_id or _active_semester_id(db)
    accounts = db.scalars(select(Account).where(Account.type.in_(balances.PAYMENT_TYPES)).order_by(Account.name))
    items = [
        {"id": a.id, "name": a.name, "type": a.type.value, "balance": balances.account_balance(db, a.id, semester_id)}
        for a in accounts
    ]
    return {"items": items, "total": sum((i["balance"] for i in items), Decimal("0.0000"))}


def kassenbereich_view(db: Session, semester_id: str | None = None) -> dict:
    semester_id = semester_id or _active_semester_id(db)
    areas = db.scalars(select(Kassenbereich).order_by(Kassenbereich.sort_order, Kassenbereich.name))
    items = [
        {
            "id": kb.id,
            "name": kb.name,
            "code": kb.code,
            "is_active": kb.is_active,
            "balance": balances.kassenbereich_balance(db, kb.id, semester_id),
        }
        for kb in areas
    ]
    return {"items": items, "total": sum((i["balance"] for i in items), Decimal("0.0000"))}


def control_equation_view(db: Session, semester_id: str | None = None) -> dict:
    semester_id = semester_id or _active_semester_id(db)
    eq = balances.control_equation(db, semester_id)
    return {
        "sum_kassenbereiche": eq["sum_kassenbereiche"],
        "liquiditaet": eq["liquiditaet"],
        "forderungen": eq["forderungen"],
        "verbindlichkeiten": eq["verbindlichkeiten"],
        "expected": eq["expected"],
        "difference": eq["difference"],
        "balanced": eq["difference"] == 0,
    }


def overdrawn_areas(db: Session, semester_id: str | None = None) -> list[dict]:
    view = kassenbereich_view(db, semester_id)
    return [
        {"id": i["id"], "name": i["name"], "balance": i["balance"], "overdraft": -i["balance"]}
        for i in view["items"]
        if i["balance"] < 0
    ]


def recent_transactions(db: Session, limit: int = 10, semester_id: str | None = None) -> list[Transaction]:
    stmt = select(Transaction).order_by(Transaction.sequential_number.desc()).limit(limit)
    if semester_id:
        stmt = stmt.where(Transaction.semester_id == semester_id)
    return list(db.scalars(stmt))


def summary(db: Session, semester_id: str | None = None) -> dict:
    semester_id = semester_id or _active_semester_id(db)
    liq = liquidity_view(db, semester_id)
    areas = kassenbereich_view(db, semester_id)
    return {
        "liquidity": liq,
        "kassenbereiche": areas,
        "control_equation": control_equation_view(db, semester_id),
        "overdrawn": overdrawn_areas(db, semester_id),
        "forderungen": balances.forderungen(db, semester_id),
        "verbindlichkeiten": balances.verbindlichkeiten(db, semester_id),
        "recent": recent_transactions(db, 10, semester_id),
    }
