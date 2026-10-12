"""Datenbestand der Kasse im Wintersemester 26/27.

Legt das laufende Semester an und richtet den Personenkreis der Kasse ein:

* **Alex Muster** – Bierkassenwart – Administrator
* **Kim Muster** – CC-Kassenwart – Administrator
* alle bereits vorhandenen Personen behalten/erhalten das Recht, ihre **eigenen
  Ausstände zu sehen** und **Rechnungen (Auslagenerstattungen) einzureichen**.

Das Skript ist idempotent und kann beliebig oft laufen.

Aufruf::

    cd backend
    python -m app.seed_ws2627
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.models.base import utcnow
from app.models.entities import Account, Beverage, Kassenbereich, Semester, Tag, User
from app.models.enums import (
    AccountType,
    MembershipStatus,
    RingColor,
    SemesterStatus,
    SemesterType,
    SystemRole,
)

SEMESTER_NAME = "WS 26/27"
SEMESTER_START = date(2026, 10, 1)
SEMESTER_END = date(2027, 3, 31)

# Kassenbereiche der Kasse
KASSENBEREICHE = [
    ("CC-Kasse", "CC", 1),
    ("Bierkasse", "BIER", 2),
    ("allgemeiner Bereich", "ALLG", 3),
    ("Veranstaltungskasse", "VERANST", 4),
    ("Hausbereich", "HAUS", 5),
]

# Buchhalterische Konten (Zahlungskonten + Erträge/Aufwände/Verrechnung)
KONTEN = [
    ("Onlinekonto", AccountType.GIRO),
    ("Barkonto CC", AccountType.CASH),
    ("Barkonto Bier", AccountType.CASH),
    ("Getränkeerlös", AccountType.REVENUE),
    ("Aufwand Getränkeeinkauf", AccountType.EXPENSE),
    ("Aufwand Bewirtung", AccountType.EXPENSE),
    ("Aufwand Auslagenerstattung", AccountType.EXPENSE),
    ("Aufwand Schwund", AccountType.EXPENSE),
    ("Verbindlichkeiten Lieferanten", AccountType.EXTERNAL),
    ("Eigenkapital", AccountType.CLEARING),
    ("Interne Umbuchung", AccountType.TRANSFER),
]

# Getränkekatalog
GETRAENKE = [
    ("St. Michaels Bräu", RingColor.RED, "0.70", "Bier"),
    ("Weizen", RingColor.YELLOW, "1.00", "Bier"),
    ("Mate", RingColor.YELLOW, "1.00", "Alkoholfrei"),
    ("Spezi", RingColor.RED, "0.70", "Alkoholfrei"),
]

# Tags (u. a. für die Zuordnung von CC-Kassen-Buchungen zu Veranstaltungen)
TAGS = [("Stiftungsfest", "accent"), ("Konvent", "muted"), ("Couleurbesuch", "warn")]

KASSENWART_PASSWORD = settings.bootstrap_admin_password   # Startpasswort der Kassenwarte
MEMBER_PASSWORD = settings.bootstrap_member_password      # Startpasswort der übrigen Personen

# Die beiden Kassenwarte – beide Administrator ihrer Kasse.
KASSENWARTE = [
    {
        "first_name": "Alex",
        "last_name": "Muster",
        "email": "bierkassenwart@example.com",
        "function": "Bierkassenwart",
    },
    {
        "first_name": "Kim",
        "last_name": "Muster",
        "email": "cc-kassenwart@example.com",
        "function": "CC-Kassenwart",
    },
]

# Übrige Personen der Kasse (Mitglieder). Bekommen Zugriff auf die eigenen
# Ausstände und dürfen Rechnungen einreichen.
MITGLIEDER = [
    {
        "first_name": "Max",
        "last_name": "Mustermann",
        "email": "max.mustermann@example.com",
        "role": SystemRole.BUCHHALTER,
        "membership_status": MembershipStatus.CB,
    },
    {
        "first_name": "Anna",
        "last_name": "Beispiel",
        "email": "anna.beispiel@example.com",
        "role": SystemRole.MITGLIED,
        "membership_status": MembershipStatus.IaCB,
    },
    {
        "first_name": "Lukas",
        "last_name": "Muster",
        "email": "lukas.muster@example.com",
        "role": SystemRole.MITGLIED,
        "membership_status": MembershipStatus.CB,
    },
]

# Rollen, die „eigene Ausstände sehen" und „Rechnungen einreichen" dürfen.
# (Eigene Ausstände sind für jede angemeldete Person sichtbar; das Einreichen
# von Erstattungen hängt an ``refund:create``.)
RIGHTS_ROLES = {
    SystemRole.ADMIN,
    SystemRole.SENIOR,
    SystemRole.BUCHHALTER,
    SystemRole.ORGANISATOR,
    SystemRole.MITGLIED,
}


def ensure_semester(db: Session) -> Semester:
    semester = db.scalar(select(Semester).where(Semester.name == SEMESTER_NAME))
    if semester is None:
        # dasselbe Zeitfenster ggf. unter altem Namen vorhanden -> umbenennen
        semester = db.scalar(
            select(Semester).where(
                Semester.start_date == SEMESTER_START, Semester.end_date == SEMESTER_END
            )
        )
        if semester is not None:
            semester.name = SEMESTER_NAME
    if semester is None:
        semester = Semester(
            name=SEMESTER_NAME,
            type=SemesterType.WINTER,
            start_date=SEMESTER_START,
            end_date=SEMESTER_END,
            status=SemesterStatus.ACTIVE,
        )
        db.add(semester)
        db.flush()

    semester.status = SemesterStatus.ACTIVE
    # es darf nur ein Semester gleichzeitig aktiv sein
    for other in db.scalars(
        select(Semester).where(Semester.id != semester.id, Semester.status == SemesterStatus.ACTIVE)
    ):
        other.status = SemesterStatus.CLOSED
        other.closed_at = utcnow()
    db.flush()
    return semester


def ensure_member_account(db: Session, user: User) -> Account:
    account = db.scalar(select(Account).where(Account.user_id == user.id))
    if account is None:
        account = Account(name=user.full_name or user.email, type=AccountType.MEMBER, user_id=user.id)
        db.add(account)
        db.flush()
    return account


def ensure_stammdaten(db: Session, semester: Semester) -> None:
    """Kassenbereiche, Konten, Getränke und Tags anlegen (idempotent)."""
    for name, code, order in KASSENBEREICHE:
        if not db.scalar(select(Kassenbereich).where(Kassenbereich.code == code)):
            db.add(Kassenbereich(name=name, code=code, sort_order=order))
    for name, acc_type in KONTEN:
        if not db.scalar(select(Account).where(Account.name == name, Account.user_id.is_(None))):
            db.add(Account(name=name, type=acc_type))
    for name, color, price, category in GETRAENKE:
        if not db.scalar(select(Beverage).where(Beverage.name == name)):
            db.add(
                Beverage(
                    name=name,
                    ring_color=color,
                    ring_price=Decimal(price),
                    category=category,
                    semester_id=semester.id,
                )
            )
    for name, color in TAGS:
        if not db.scalar(select(Tag).where(Tag.name == name)):
            db.add(Tag(name=name, color=color))
    db.flush()


def ensure_mitglied(db: Session, spec: dict) -> tuple[User, bool]:
    """Legt eine Person der Kasse an (falls noch nicht vorhanden)."""
    user = db.scalar(select(User).where(User.email == spec["email"]))
    created = False
    if user is None:
        user = User(
            email=spec["email"],
            password_hash=hash_password(MEMBER_PASSWORD),
            first_name=spec["first_name"],
            last_name=spec["last_name"],
            membership_status=spec["membership_status"],
            system_role=spec["role"],
            is_active=True,
            activated_at=utcnow(),
        )
        db.add(user)
        db.flush()
        created = True
    else:
        user.is_active = True
    ensure_member_account(db, user)
    db.flush()
    return user, created


def ensure_kassenwart(db: Session, spec: dict) -> tuple[User, bool]:
    user = db.scalar(select(User).where(User.email == spec["email"]))
    created = False
    note = f"Kassenwart: {spec['function']}"
    if user is None:
        user = User(
            email=spec["email"],
            password_hash=hash_password(KASSENWART_PASSWORD),
            first_name=spec["first_name"],
            last_name=spec["last_name"],
            membership_status=MembershipStatus.CB,
            system_role=SystemRole.ADMIN,
            is_active=True,
            activated_at=utcnow(),
            notes=note,
        )
        db.add(user)
        db.flush()
        created = True
    else:
        user.system_role = SystemRole.ADMIN
        user.is_active = True
        if note not in (user.notes or ""):
            user.notes = note if not user.notes else f"{note}\n{user.notes}"
    ensure_member_account(db, user)
    db.flush()
    return user, created


LEGACY_EMAIL_DOMAIN = "@bierkasse.local"
VALID_EMAIL_DOMAIN = "@example.com"


def normalize_legacy_emails(db: Session) -> list[tuple[str, str]]:
    """``@bierkasse.local`` ist für die Login-Validierung ungültig und würde die
    betroffenen Personen aussperren. Solche Adressen werden auf die gültige
    Domain umgestellt."""
    renamed: list[tuple[str, str]] = []
    for user in db.scalars(select(User)):
        if not user.email.endswith(LEGACY_EMAIL_DOMAIN):
            continue
        new_email = user.email[: -len(LEGACY_EMAIL_DOMAIN)] + VALID_EMAIL_DOMAIN
        if db.scalar(select(User).where(User.email == new_email)):
            continue  # Zieladresse existiert schon
        renamed.append((user.email, new_email))
        user.email = new_email
    db.flush()
    return renamed


def grant_rights_to_everyone(db: Session) -> list[str]:
    """Jede vorhandene Person darf ihre eigenen Ausstände sehen und
    Rechnungen einreichen (Rolle mit ``refund:create``, Konto vorhanden)."""
    changed: list[str] = []
    for user in db.scalars(select(User)):
        touched = False
        if not user.is_active:
            user.is_active = True
            user.activated_at = user.activated_at or utcnow()
            touched = True
        if user.system_role not in RIGHTS_ROLES:
            user.system_role = SystemRole.MITGLIED
            touched = True
        ensure_member_account(db, user)
        if touched:
            changed.append(user.email)
    db.flush()
    return changed


def retire_technical_admin(db: Session) -> str | None:
    """Das technische Bootstrap-Konto (admin@…) ist keine Person.

    Damit es genau die **zwei** Kassenwarte als Administratoren gibt, wird das
    technische Konto deaktiviert und auf die Rolle ``senior`` zurückgestuft.
    """
    from app.config import settings

    if settings.bootstrap_admin_email in {w["email"] for w in KASSENWARTE}:
        return None
    user = db.scalar(select(User).where(User.email == settings.bootstrap_admin_email))
    if user is None or not user.is_active:
        return None
    user.is_active = False
    if user.system_role == SystemRole.ADMIN:
        user.system_role = SystemRole.SENIOR
    db.flush()
    return user.email


def seed(db: Session) -> dict:
    semester = ensure_semester(db)
    ensure_stammdaten(db, semester)
    renamed = normalize_legacy_emails(db)
    wardens = [ensure_kassenwart(db, spec) for spec in KASSENWARTE]
    members = [ensure_mitglied(db, spec) for spec in MITGLIEDER]
    changed = grant_rights_to_everyone(db)
    retired = retire_technical_admin(db)
    db.commit()

    admins = list(db.scalars(select(User).where(User.system_role == SystemRole.ADMIN)))
    everyone = list(db.scalars(select(User).order_by(User.last_name, User.first_name)))
    return {
        "semester": semester.name,
        "wardens": [w[0] for w in wardens],
        "members": [m[0] for m in members],
        "changed": changed,
        "retired": retired,
        "renamed": renamed,
        "admins": admins,
        "everyone": everyone,
    }


def main() -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        result = seed(db)
        print(f"Semester: {result['semester']} (aktiv)")
        print(f"Administratoren ({len(result['admins'])}):")
        for admin in result["admins"]:
            function = admin.notes.splitlines()[0] if admin.notes else "Administrator"
            print(f"  • {admin.full_name:<22} {admin.email:<32} {function}")
        print("Personen mit Zugriff auf eigene Ausstände + Rechnungseinreichung:")
        for user in result["everyone"]:
            state = "" if user.is_active else "  (inaktiv)"
            print(f"  • {user.full_name:<22} {user.system_role.value:<12} {user.email}{state}")
        if result["changed"]:
            print("Angepasst:", ", ".join(result["changed"]))
        if result["retired"]:
            print(f"Technisches Konto deaktiviert: {result['retired']}")
        for old, new in result["renamed"]:
            print(f"E-Mail korrigiert: {old} -> {new}")


if __name__ == "__main__":
    main()
