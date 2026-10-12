from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.permissions import KASSENBEREICH_MANAGE, READ_ALL
from app.database import get_db
from app.models.entities import Account, User
from app.schemas.accounting import AccountBalanceOut, AccountCreate, AccountOut
from app.services import balances

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountBalanceOut])
def list_accounts(db: Session = Depends(get_db), _: User = Depends(require_permission(READ_ALL))):
    accounts = db.scalars(select(Account).order_by(Account.type, Account.name))
    return [
        AccountBalanceOut(account=AccountOut.model_validate(a), balance=balances.account_balance(db, a.id))
        for a in accounts
    ]


@router.post("", response_model=AccountOut, status_code=201)
def create_account(
    payload: AccountCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(KASSENBEREICH_MANAGE))
):
    account = Account(**payload.model_dump())
    db.add(account)
    db.flush()
    return account


@router.get("/{account_id}/balance", response_model=AccountBalanceOut)
def account_balance(account_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(READ_ALL))):
    account = db.get(Account, account_id)
    if not account:
        from app.core.errors import NotFoundError

        raise NotFoundError("Konto nicht gefunden.")
    return AccountBalanceOut(account=AccountOut.model_validate(account), balance=balances.account_balance(db, account_id))
