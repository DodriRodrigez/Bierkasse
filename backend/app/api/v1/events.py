from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import EVENT_CREATE
from app.database import get_db
from app.models.entities import Event, Tag, User
from app.schemas.features import EventCreate, EventOut
from app.services import posting_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Event).order_by(Event.date.desc())))


@router.post("", response_model=EventOut, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(require_permission(EVENT_CREATE))):
    event = Event(
        date=payload.date,
        name=payload.name,
        type=payload.type,
        organizer_id=user.id,
        signature=payload.signature,
        payer_type=payload.payer_type,
        payer_user_id=payload.payer_user_id,
        red_glasses=payload.red_glasses,
        yellow_glasses=payload.yellow_glasses,
        donation=payload.donation,
        kassenbereich_id=payload.kassenbereich_id,
        semester_id=payload.semester_id,
        created_by_id=user.id,
    )
    db.add(event)
    db.flush()
    for name in payload.tags:
        tag = db.scalar(select(Tag).where(Tag.name == name))
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            db.flush()
        event.tags.append(tag)
    db.flush()
    if payload.post:
        posting_service.post_event(db, event, user)
    return event


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise NotFoundError("Veranstaltung nicht gefunden.")
    return event


@router.post("/{event_id}/post", response_model=EventOut)
def post_event(event_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = db.get(Event, event_id)
    if not event:
        raise NotFoundError("Veranstaltung nicht gefunden.")
    posting_service.post_event(db, event, user)
    return event
