"""Role and permission model.

Roles map onto a set of granular permission strings.  The API never checks
roles directly for business operations; it checks permissions so that the role
matrix can evolve without touching route handlers.
"""
from __future__ import annotations

from app.models.enums import SystemRole

# --- permission catalogue -------------------------------------------------
BOOKING_READ = "booking:read"
BOOKING_CREATE = "booking:create"
BOOKING_STORNO = "booking:storno"
BOOKING_LOCK = "booking:lock"
BOOKING_APPROVE = "booking:approve"
KASSENBEREICH_MANAGE = "kassenbereich:manage"
TAG_MANAGE = "tag:manage"
TRANSFER_CREATE = "transfer:create"
RING_COUNT_CREATE = "ringcount:create"
RING_COUNT_POST = "ringcount:post"
EVENT_CREATE = "event:create"
DELIVERY_CREATE = "delivery:create"
DELIVERY_APPROVE = "delivery:approve"
INVENTORY_CREATE = "inventory:create"
INVENTORY_APPROVE = "inventory:approve"
REFUND_CREATE = "refund:create"
REFUND_APPROVE = "refund:approve"
SEMESTER_MANAGE = "semester:manage"
SEMESTER_CLOSE = "semester:close"
USER_MANAGE = "user:manage"
AUDIT_READ = "audit:read"
DASHBOARD_FULL = "dashboard:full"

READ_ALL = "read:all"

ROLE_PERMISSIONS: dict[SystemRole, set[str]] = {
    SystemRole.ADMIN: {
        BOOKING_READ, BOOKING_CREATE, BOOKING_STORNO, BOOKING_LOCK, BOOKING_APPROVE,
        KASSENBEREICH_MANAGE, TAG_MANAGE, TRANSFER_CREATE,
        RING_COUNT_CREATE, RING_COUNT_POST, EVENT_CREATE,
        DELIVERY_CREATE, DELIVERY_APPROVE, INVENTORY_CREATE, INVENTORY_APPROVE,
        REFUND_CREATE, REFUND_APPROVE, SEMESTER_MANAGE, SEMESTER_CLOSE,
        USER_MANAGE, AUDIT_READ, DASHBOARD_FULL, READ_ALL,
    },
    SystemRole.SENIOR: {
        BOOKING_READ, BOOKING_CREATE, BOOKING_STORNO, BOOKING_APPROVE, TRANSFER_CREATE,
        RING_COUNT_POST, EVENT_CREATE, DELIVERY_APPROVE, INVENTORY_APPROVE,
        REFUND_APPROVE, SEMESTER_CLOSE, DASHBOARD_FULL, READ_ALL,
    },
    SystemRole.BUCHHALTER: {
        BOOKING_READ, BOOKING_CREATE, BOOKING_STORNO, TRANSFER_CREATE,
        RING_COUNT_CREATE, RING_COUNT_POST, EVENT_CREATE,
        DELIVERY_CREATE, INVENTORY_CREATE, REFUND_CREATE, DASHBOARD_FULL, READ_ALL,
    },
    SystemRole.ORGANISATOR: {
        BOOKING_READ, BOOKING_CREATE, RING_COUNT_CREATE, EVENT_CREATE, DELIVERY_CREATE, INVENTORY_CREATE,
        REFUND_CREATE,
    },
    SystemRole.MITGLIED: {BOOKING_CREATE, REFUND_CREATE},
    SystemRole.GAST: set(),
}


def permissions_for(role: SystemRole) -> set[str]:
    return set(ROLE_PERMISSIONS.get(role, set()))


def has_permission(role: SystemRole, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return permission in perms or READ_ALL in perms
