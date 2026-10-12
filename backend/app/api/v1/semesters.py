from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.core.permissions import SEMESTER_CLOSE, SEMESTER_MANAGE
from app.database import get_db
from app.models.base import utcnow
from app.models.entities import Semester, User
from app.models.enums import SemesterStatus
from app.schemas.features import SemesterCreate, SemesterOut

router = APIRouter(prefix="/semesters", tags=["semesters"])


@router.get("", response_model=list[SemesterOut])
def list_semesters(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return list(db.scalars(select(Semester).order_by(Semester.start_date.desc())))


@router.get("/current", response_model=SemesterOut | None)
def current_semester(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalar(select(Semester).where(Semester.status == SemesterStatus.ACTIVE))


@router.post("", response_model=SemesterOut, status_code=201)
def create_semester(
    payload: SemesterCreate, db: Session = Depends(get_db), _: User = Depends(require_permission(SEMESTER_MANAGE))
):
    if payload.start_date >= payload.end_date:
        raise ValidationError("Startdatum muss vor dem Enddatum liegen.")
    if db.scalar(select(Semester).where(Semester.name == payload.name)):
        raise ConflictError("Semester-Name existiert bereits.")
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.flush()
    return semester


@router.post("/{semester_id}/close", response_model=SemesterOut)
def close_semester(
    semester_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission(SEMESTER_CLOSE)),
):
    semester = db.get(Semester, semester_id)
    if not semester:
        raise NotFoundError("Semester nicht gefunden.")
    semester.status = SemesterStatus.CLOSED
    semester.closed_at = utcnow()
    semester.closed_by_id = user.id
    db.flush()
    return semester
