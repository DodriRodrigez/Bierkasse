from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core.errors import NotFoundError
from app.core.permissions import AUDIT_READ, DASHBOARD_FULL
from app.database import get_db
from app.models.entities import AuditLog, Notification, User
from app.schemas.features import AuditLogOut, NotificationOut
from app.services import email_service

router = APIRouter(tags=["admin"])


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(limit: int = 100, db: Session = Depends(get_db), _: User = Depends(require_permission(AUDIT_READ))):
    return list(db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)))


@router.post("/notifications/settlement")
def send_settlement_to_all(db: Session = Depends(get_db), _: User = Depends(require_permission(DASHBOARD_FULL))):
    """Verrechnungs-Automat: Ausstandsaufstellung an alle aktiven Personen."""
    results = [
        email_service.send_settlement_email(db, user)
        for user in db.scalars(select(User).where(User.is_active.is_(True)))
    ]
    return {
        "count": len(results),
        "delivered": sum(1 for r in results if r["delivered"]),
        "results": [
            {"to": r["to"], "subject": r["subject"], "delivered": r["delivered"], "transport": r["transport"]}
            for r in results
        ],
    }


@router.get("/notifications", response_model=list[NotificationOut])
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(
        db.scalars(
            select(Notification).where(Notification.user_id == user.id).order_by(Notification.created_at.desc())
        )
    )


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    notification = db.get(Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise NotFoundError("Benachrichtigung nicht gefunden.")
    notification.is_read = True
    db.flush()
    return notification
