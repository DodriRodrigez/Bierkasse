from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import READ_ALL, USER_MANAGE
from app.core.security import hash_password
from app.database import get_db
from app.models.base import utcnow
from app.models.entities import Account, Kassenbereich, Transaction, TransactionLine, User
from app.models.enums import AccountType, Side
from app.schemas.users import (
    MemberBalanceArea,
    MemberDashboard,
    MemberTransactionRow,
    SettlementEmailRequest,
    SettlementEmailResult,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import balances, email_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_permission(USER_MANAGE))):
    return list(db.scalars(select(User).order_by(User.last_name, User.first_name)))


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(USER_MANAGE))
):
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-Mail ist bereits registriert.")
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        first_name=payload.first_name,
        last_name=payload.last_name,
        membership_status=payload.membership_status,
        system_role=payload.system_role,
        is_active=payload.is_active,
        activated_at=utcnow() if payload.is_active else None,
    )
    db.add(user)
    db.flush()
    _ensure_member_account(db, user)
    db.flush()
    return user


@router.get("/me/dashboard", response_model=MemberDashboard)
def my_dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    by_area = balances.member_balance_by_kassenbereich(db, user.id)
    areas = {kb.id: kb for kb in db.scalars(select(Kassenbereich))}
    rows = [
        MemberBalanceArea(kassenbereich_id=kb_id, name=areas[kb_id].name if kb_id in areas else kb_id, balance=bal)
        for kb_id, bal in by_area.items()
    ]
    account = user.account
    recent: list[MemberTransactionRow] = []
    if account:
        lines = db.scalars(
            select(TransactionLine)
            .where(TransactionLine.account_id == account.id)
            .order_by(TransactionLine.created_at.desc())
            .limit(10)
        ).all()
        for line in lines:
            txn = db.get(Transaction, line.transaction_id)
            recent.append(
                MemberTransactionRow(
                    id=txn.id,
                    sequential_number=txn.sequential_number,
                    date=txn.date.isoformat(),
                    description=line.description or txn.description,
                    amount=line.amount,
                    side=line.side.value,
                )
            )
    return MemberDashboard(
        user=UserOut.model_validate(user),
        total_balance=balances.member_total_balance(db, user.id),
        by_kassenbereich=rows,
        recent_transactions=recent,
    )


@router.post("/me/settlement-email", response_model=SettlementEmailResult)
def settlement_email(
    payload: SettlementEmailRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sendet die eigene Ausstandsaufstellung per E-Mail (Verrechnungs-Automat)."""
    return email_service.send_settlement_email(
        db, user, to=payload.to, semester_id=payload.semester_id
    )


@router.get("/directory")
def directory(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Lightweight member list for pickers (Ringbrett, Veranstaltungen)."""
    users = db.scalars(select(User).where(User.is_active.is_(True)).order_by(User.last_name, User.first_name))
    return [
        {"id": u.id, "name": u.full_name, "membership_status": u.membership_status.value}
        for u in users
    ]



@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(READ_ALL))):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Benutzer nicht gefunden.")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Benutzer nicht gefunden.")
    is_admin = current.system_role.value == "admin"
    if not is_admin and current.id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Keine Berechtigung.")
    data = payload.model_dump(exclude_unset=True)
    if not is_admin:
        data = {k: v for k, v in data.items() if k in {"first_name", "last_name", "phone", "iban", "notes"}}
    for key, value in data.items():
        setattr(user, key, value)
    if is_admin and payload.is_active:
        user.activated_at = user.activated_at or utcnow()
    db.flush()
    if user.is_active:
        _ensure_member_account(db, user)
        db.flush()
    return user


@router.post("/{user_id}/activate", response_model=UserOut)
def activate(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(USER_MANAGE))):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Benutzer nicht gefunden.")
    user.is_active = True
    user.activated_at = utcnow()
    db.flush()
    _ensure_member_account(db, user)
    db.flush()
    return user


@router.post("/{user_id}/deactivate", response_model=UserOut)
def deactivate(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(USER_MANAGE))):
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError("Benutzer nicht gefunden.")
    user.is_active = False
    db.flush()
    return user


def _ensure_member_account(db: Session, user: User) -> Account:
    account = db.scalar(select(Account).where(Account.user_id == user.id))
    if account:
        return account
    account = Account(name=user.full_name or user.email, type=AccountType.MEMBER, user_id=user.id)
    db.add(account)
    db.flush()
    return account
