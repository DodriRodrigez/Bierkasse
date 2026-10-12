from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import RING_COUNT_CREATE
from app.database import get_db
from app.models.entities import RingbrettEntry, RingbrettSession, User
from app.schemas.features import RingbrettCreate, RingbrettOut
from app.services import posting_service

router = APIRouter(prefix="/ringbrett-sessions", tags=["ringbrett"])


@router.get("", response_model=list[RingbrettOut])
def list_sessions(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    stmt = select(RingbrettSession).options(selectinload(RingbrettSession.entries)).order_by(
        RingbrettSession.date.desc(), RingbrettSession.zaehlungsnummer.desc()
    )
    return list(db.scalars(stmt))


@router.post("", response_model=RingbrettOut, status_code=201)
def create_session(
    payload: RingbrettCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(RING_COUNT_CREATE))
):
    existing = db.scalar(
        select(func.count(RingbrettSession.id)).where(RingbrettSession.semester_id == payload.semester_id)
    ) if payload.semester_id else 0
    session = RingbrettSession(
        date=payload.date,
        counted_by_id=user.id,
        semester_id=payload.semester_id,
        kassenbereich_id=payload.kassenbereich_id,
        zaehlungsnummer=(existing or 0) + 1,
        notes=payload.notes,
    )
    db.add(session)
    db.flush()
    for entry in payload.entries:
        db.add(
            RingbrettEntry(
                session_id=session.id,
                user_id=entry.user_id,
                red_rings=entry.red_rings,
                yellow_rings=entry.yellow_rings,
            )
        )
    db.flush()
    return session


@router.get("/{session_id}", response_model=RingbrettOut)
def get_session(session_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    session = db.get(RingbrettSession, session_id)
    if not session:
        raise NotFoundError("Zählung nicht gefunden.")
    return session


@router.post("/{session_id}/post", response_model=RingbrettOut)
def post_session(session_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.get(RingbrettSession, session_id)
    if not session:
        raise NotFoundError("Zählung nicht gefunden.")
    posting_service.post_ringbrett(db, session, user)
    return session
