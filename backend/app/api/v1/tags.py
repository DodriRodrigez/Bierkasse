from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import ConflictError, NotFoundError
from app.core.permissions import TAG_MANAGE
from app.database import get_db
from app.models.entities import Tag, User
from app.schemas.accounting import TagCreate, TagOut

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
def list_tags(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Tag).order_by(Tag.name)))


@router.post("", response_model=TagOut, status_code=201)
def create_tag(payload: TagCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(TAG_MANAGE))):
    if db.scalar(select(Tag).where(Tag.name == payload.name)):
        raise ConflictError("Tag existiert bereits.")
    tag = Tag(**payload.model_dump())
    db.add(tag)
    db.flush()
    return tag


@router.delete("/{tag_id}", status_code=204)
def delete_tag(tag_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission(TAG_MANAGE))):
    tag = db.get(Tag, tag_id)
    if not tag:
        raise NotFoundError("Tag nicht gefunden.")
    db.delete(tag)
