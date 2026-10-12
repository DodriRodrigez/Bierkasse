"""WS26-Datenimport.

Pflegt die Daten aus ``WS26_Data/`` in das Semester **WS26** ein:

* die beiden **Eröffnungssalden** (Altsystem „Barkonto", Stand 20.08.2026) für
  Bierkasse und CC-Kasse, je als *eine* Eröffnungsbuchung,
* die **Kontoauszüge** der drei C24-Konten (09/2026 und 10/2026) — jede
  Auszugszeile als eigene, ausgeglichene Buchung.

Die Daten werden aus den PDF-Dateien gelesen (Textlayer, via ``pdftotext``).

Fehlt der Ordner ``WS26_Data/`` (z. B. in einer frischen Checkout ohne die
privaten Originaldaten), wird der Import ohne Fehler übersprungen.

Das Skript ist idempotent: jede erzeugte Buchung trägt eine ``migration_source``-
Kennung; bereits vorhandene Kennungen werden übersprungen.

Aufruf (aus ``backend/``)::

    python -m app.import_ws26 --dry-run     # nur anzeigen
    python -m app.import_ws26               # schreiben

Ziel-Datenbank ist die über ``BIERKASSE7_DATABASE_URL`` gesetzte (siehe
``app.config``); ohne Vorgabe ``backend/bierkasse7.db``.
"""
from __future__ import annotations

import argparse
import re
import subprocess
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.money import to_decimal
from app.core.security import hash_password
from app.database import SessionLocal
from app.models.base import utcnow
from app.models.entities import Account, Kassenbereich, Semester, Transaction, User
from app.models.enums import (
    AccountType,
    MembershipStatus,
    SemesterStatus,
    SemesterType,
    Side,
    SystemRole,
    TransactionCategory,
)
from app.services import accounting_service
from app.services.accounting_service import LineInput

# --------------------------------------------------------------------------
# Rahmen
# --------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "WS26_Data"

SEMESTER_NAME = "WS 26/27"
SEMESTER_START = date(2026, 8, 20)   # Datum des Eröffnungssaldos
SEMESTER_END = date(2027, 3, 31)
OPENING_DATE = date(2026, 8, 20)
STATEMENT_YEAR = 2026

KASSE_BK = "BIER"
KASSE_CC = "CC"
KASSE_ALLG = "ALLG"

# Eröffnungssalden: Datei -> Kassenbereich
OPENING_FILES = [
    ("Eröffnungssaldo_CC_WS26_260820.pdf", KASSE_CC),
    ("Eröffnungssaldo_BK_WS26_260820.pdf", KASSE_BK),
]

# Kontoauszüge: Datei -> (Kassenbereich, Name des Bankkontos)
STATEMENT_FILES = [
    ("Kontoauszug_2026-09_BK_Konto.pdf", KASSE_BK, "BK Konto (C24)"),
    ("Kontoauszug_2026-09_CC_Kasse.pdf", KASSE_CC, "CC Kasse (C24)"),
    ("Kontoauszug_2026-09_CTD_BK_und_CCK.pdf", KASSE_ALLG, "CTD BK und CCK (C24)"),
    ("Kontoauszug_2026-10_BK_Konto.pdf", KASSE_BK, "BK Konto (C24)"),
    ("Kontoauszug_2026-10_CC_Kasse.pdf", KASSE_CC, "CC Kasse (C24)"),
    ("Kontoauszug_2026-10_CTD_BK_und_CCK.pdf", KASSE_ALLG, "CTD BK und CCK (C24)"),
]

# Buchhalterische Standardkonten, die der Import zusätzlich benötigt
EXTRA_ACCOUNTS = [
    ("Sonstige Erträge", AccountType.REVENUE),
    ("Sonstiger Aufwand", AccountType.EXPENSE),
]

MEMBER_PASSWORD = settings.bootstrap_member_password


# --------------------------------------------------------------------------
# PDF-Text
# --------------------------------------------------------------------------
def pdf_text(path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext fehlgeschlagen für {path}: {result.stderr.strip()}")
    return result.stdout


_AMOUNT = re.compile(r"([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s*€\s*$")


def _to_decimal(raw: str) -> Decimal:
    return Decimal(raw.replace(".", "").replace(",", "."))


def parse_opening(text: str) -> list[tuple[str, Decimal]]:
    """Eröffnungssaldo-Zeilen ``Name  Betrag €`` (Summenzeile ohne Name ignoriert)."""
    rows: list[tuple[str, Decimal]] = []
    for line in text.splitlines():
        m = _AMOUNT.search(line)
        if not m:
            continue
        name = line[: m.start()].strip()
        if not name or name.lower().startswith("kontoname"):
            continue
        rows.append((name, _to_decimal(m.group(1))))
    return rows


_TXN_START = re.compile(
    r"^\s*(\d{2})\.(\d{2})\.\s+\d{2}\.\d{2}\.\s+(.*?)\s{2,}([+-]?\d{1,3}(?:\.\d{3})*,\d{2})\s*€\s*$"
)


def parse_statement(text: str) -> list[dict]:
    """Transaktionsübersicht eines Kontoauszugs in Einzelzeilen zerlegen."""
    lines = text.splitlines()
    txns: list[dict] = []
    in_block = False
    for line in lines:
        if "Transaktionsübersicht" in line:
            in_block = True
            continue
        if not in_block:
            continue
        if "Zusammenfassung" in line or line.startswith("\f"):
            in_block = False
            continue
        m = _TXN_START.match(line)
        if m:
            day, month = int(m.group(1)), int(m.group(2))
            desc = m.group(3).strip()
            amount = _to_decimal(m.group(4))
            txns.append(
                {
                    "date": date(STATEMENT_YEAR, month, day),
                    "description": desc,
                    "amount": amount,
                    "details": [],
                }
            )
        elif txns and line.strip() and not _AMOUNT.search(line):
            txns[-1]["details"].append(line.strip())
    return txns


# --------------------------------------------------------------------------
# Stammdaten
# --------------------------------------------------------------------------
def ensure_semester(db: Session) -> Semester:
    semester = db.scalar(select(Semester).where(Semester.name == SEMESTER_NAME))
    if semester is None:
        # bestehendes WS-26/27-Semester übernehmen und umbenennen
        semester = db.scalar(
            select(Semester).where(
                Semester.start_date == date(2026, 10, 1), Semester.end_date == date(2027, 3, 31)
            )
        )
    if semester is None:
        semester = Semester(
            name=SEMESTER_NAME, type=SemesterType.WINTER,
            start_date=SEMESTER_START, end_date=SEMESTER_END,
        )
        db.add(semester)
    semester.name = SEMESTER_NAME
    semester.start_date = SEMESTER_START
    semester.end_date = SEMESTER_END
    semester.status = SemesterStatus.ACTIVE
    db.flush()
    for other in db.scalars(
        select(Semester).where(Semester.id != semester.id, Semester.status == SemesterStatus.ACTIVE)
    ):
        other.status = SemesterStatus.CLOSED
        other.closed_at = utcnow()
    db.flush()
    return semester


def ensure_kassenbereich(db: Session, code: str) -> Kassenbereich:
    kb = db.scalar(select(Kassenbereich).where(Kassenbereich.code == code))
    if kb is None:
        names = {KASSE_BK: "Bierkasse", KASSE_CC: "CC-Kasse", KASSE_ALLG: "allgemeiner Bereich"}
        kb = Kassenbereich(name=names[code], code=code)
        db.add(kb)
        db.flush()
    return kb


def ensure_account(db: Session, name: str, type_: AccountType) -> Account:
    account = db.scalar(select(Account).where(Account.name == name, Account.type == type_))
    if account is None:
        account = Account(name=name, type=type_)
        db.add(account)
        db.flush()
    return account


def ensure_member_account(db: Session, user: User) -> Account:
    account = db.scalar(select(Account).where(Account.user_id == user.id))
    if account is None:
        account = Account(name=user.full_name or user.email, type=AccountType.MEMBER, user_id=user.id)
        db.add(account)
        db.flush()
    return account


# --------------------------------------------------------------------------
# Zuordnung der Eröffnungssaldo-Konten
# --------------------------------------------------------------------------
_STATUS_PREFIXES = [
    ("AH-IdC", MembershipStatus.AH_IdC),
    ("IaCB", MembershipStatus.IaCB),
    ("FCBr", MembershipStatus.FcK),
    ("FCK", MembershipStatus.FcK),
    ("AH", MembershipStatus.AH),
    ("IdC", MembershipStatus.IdC),
    ("CB", MembershipStatus.CB),
    ("Spef", MembershipStatus.Spef),
    ("F", MembershipStatus.F),
]
_SALUTATIONS = ("Frau", "Herr")

_email_seq = 0


def _classify(name: str) -> tuple[str, MembershipStatus | None, str]:
    """(art, status, personenname). art ∈ {asset, external, person}."""
    if re.match(r"^\d", name):
        return "asset", None, name
    if name.startswith("C!") or "verein" in name.lower() or name.startswith("Wohnheim"):
        return "external", None, name
    for prefix, status in _STATUS_PREFIXES:
        if name.upper() == prefix.upper() or name.upper().startswith(prefix.upper() + " "):
            person = name[len(prefix):].strip() or prefix
            return "person", status, person
    for sal in _SALUTATIONS:
        if name.startswith(sal + " "):
            return "person", MembershipStatus.CB, name[len(sal):].strip()
    return "person", MembershipStatus.CB, name


def _person_user(db: Session, person: str, status: MembershipStatus) -> User:
    """Person anhand des (vollständigen) Namens finden oder anlegen."""
    global _email_seq
    person = person.strip()
    user = db.scalar(select(User).where(User.last_name == person))
    if user is not None:
        return user
    _email_seq += 1
    email = f"import.{person.lower().replace(' ', '')}.{_email_seq}@example.com"
    user = User(
        email=email,
        password_hash=hash_password(MEMBER_PASSWORD),
        first_name="",
        last_name=person,
        membership_status=status,
        system_role=SystemRole.MITGLIED,
        is_active=True,
        activated_at=utcnow(),
    )
    db.add(user)
    db.flush()
    ensure_member_account(db, user)
    return user


def resolve_opening_account(db: Session, name: str) -> tuple[Account, str]:
    art, status, person = _classify(name)
    if art == "asset":
        type_ = AccountType.GIRO if "online" in name.lower() else AccountType.CASH
        return ensure_account(db, name, type_), "asset"
    if art == "external":
        return ensure_account(db, name, AccountType.EXTERNAL), "external"
    user = _person_user(db, person, status or MembershipStatus.CB)
    return ensure_member_account(db, user), "person"


# --------------------------------------------------------------------------
# Gegenkonto für Kontoauszugs-Zeilen
# --------------------------------------------------------------------------
def resolve_counter(db: Session, desc: str) -> tuple[Account, bool]:
    """(Gegenkonto, ist_interne_umbuchung) anhand der Transaktionsinformation."""
    text = desc.lower()
    transfer = ensure_account(db, "Interne Umbuchung", AccountType.TRANSFER)
    eigenkapital = ensure_account(db, "Eigenkapital", AccountType.CLEARING)

    if "kassenübergabe" in text:
        return eigenkapital, False
    if "einzahlung bierkasse" in text:
        return ensure_account(db, "Barkonto Bier", AccountType.CASH), False
    if "einzahlung cc kasse" in text:
        return ensure_account(db, "Barkonto CC", AccountType.CASH), False
    if "zinsen" in text:
        return ensure_account(db, "Sonstige Erträge", AccountType.REVENUE), False
    if "steuern" in text:
        return ensure_account(db, "Sonstiger Aufwand", AccountType.EXPENSE), False
    if "flaschenp" in text:
        return ensure_account(db, "Aufwand Getränkeeinkauf", AccountType.EXPENSE), False
    if "tim mustermann" in text:
        return ensure_account(db, "Aufwand Auslagenerstattung", AccountType.EXPENSE), False
    if "rostock" in text:
        if "rostock mustermann" in text:
            last_name = "Mustermann"
        elif "rostock musterfrau" in text:
            last_name = "Musterfrau"
        else:
            last_name = None
        user = db.scalar(select(User).where(User.last_name == last_name)) if last_name else None
        if user is not None:
            return ensure_member_account(db, user), False
        return eigenkapital, False
    # Überweisung zwischen eigenen C24-Konten
    if any(k in text for k in ("bk konto", "ctd bk und cck", "cc kasse")):
        return transfer, True
    return eigenkapital, False


# --------------------------------------------------------------------------
# Buchungen
# --------------------------------------------------------------------------
def _existing(db: Session, source: str) -> bool:
    return db.scalar(select(Transaction).where(Transaction.migration_source == source)) is not None


def _post(db: Session, user: User, semester: Semester, *, date_, source, description, lines,
          internal=False):
    if _existing(db, source):
        return None
    result = accounting_service.create_transaction(
        db, date_=date_, description=description, category=TransactionCategory.MISC,
        lines=lines, user=user, semester_id=semester.id,
        is_internal_transfer=internal, lock=True,
    )
    result.transaction.migration_source = source
    db.flush()
    return result.transaction


def import_opening(db: Session, user: User, semester: Semester) -> int:
    count = 0
    for filename, kb_code in OPENING_FILES:
        path = DATA_DIR / filename
        rows = parse_opening(pdf_text(path))
        kb = ensure_kassenbereich(db, kb_code)
        source = f"ws26:opening:{kb_code}"
        if _existing(db, source):
            continue
        lines: list[LineInput] = []
        net = Decimal("0.0000")
        for name, amount in rows:
            account, _ = resolve_opening_account(db, name)
            if amount == 0:
                continue
            net += amount
            lines.append(LineInput(
                account_id=account.id,
                side=Side.SOLL if amount > 0 else Side.HABEN,
                amount=abs(amount),
                kassenbereich_id=kb.id,
                description=name,
            ))
        if net != 0:
            ek = ensure_account(db, "Eigenkapital", AccountType.CLEARING)
            lines.append(LineInput(
                account_id=ek.id,
                side=Side.HABEN if net > 0 else Side.SOLL,
                amount=abs(net),
                kassenbereich_id=kb.id,
                description="Eröffnungssaldo",
            ))
        _post(db, user, semester, date_=OPENING_DATE, source=source,
              description=f"Eröffnungssaldo {kb.name} (Altsystem, 20.08.2026)", lines=lines)
        count += 1
    return count


def import_statements(db: Session, user: User, semester: Semester) -> int:
    count = 0
    for filename, kb_code, account_name in STATEMENT_FILES:
        path = DATA_DIR / filename
        bank = ensure_account(db, account_name, AccountType.GIRO)
        kb = ensure_kassenbereich(db, kb_code)
        for idx, txn in enumerate(parse_statement(pdf_text(path)), start=1):
            source = f"ws26:konto:{filename}:{idx:02d}"
            if _existing(db, source):
                continue
            full = " / ".join([txn["description"], *txn["details"]])
            counter, internal = resolve_counter(db, full)
            amount = abs(txn["amount"])
            if txn["amount"] > 0:
                bank_line = LineInput(bank.id, Side.SOLL, amount, kb.id, description=txn["description"])
                counter_side = Side.HABEN
            else:
                bank_line = LineInput(bank.id, Side.HABEN, amount, kb.id, description=txn["description"])
                counter_side = Side.SOLL
            lines = [
                bank_line,
                LineInput(counter.id, counter_side, amount, kb.id, description=txn["description"]),
            ]
            _post(db, user, semester, date_=txn["date"], source=source,
                  description=full[:500], lines=lines, internal=internal)
            count += 1
    return count


# --------------------------------------------------------------------------
def run(dry_run: bool = False) -> dict:
    if not DATA_DIR.exists():
        return {"semester": None, "openings": 0, "statements": 0,
                "dry_run": dry_run, "skipped": True}
    with SessionLocal() as db:
        semester = ensure_semester(db)
        warden = db.scalar(select(User).where(User.system_role == SystemRole.ADMIN))
        if warden is None:
            raise RuntimeError("Kein Administrator gefunden (Seed ausführen).")
        openings = import_opening(db, warden, semester)
        statements = import_statements(db, warden, semester)
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return {"semester": semester.name, "openings": openings, "statements": statements,
                "dry_run": dry_run}


def main() -> None:
    parser = argparse.ArgumentParser(description="WS26-Datenimport")
    parser.add_argument("--dry-run", action="store_true", help="nur anzeigen, nicht schreiben")
    args = parser.parse_args()
    result = run(dry_run=args.dry_run)
    prefix = "[dry-run] " if result["dry_run"] else ""
    if result.get("skipped"):
        print(f"{prefix}Kein Datenverzeichnis {DATA_DIR} – WS26-Import übersprungen.")
        return
    print(f"{prefix}Semester: {result['semester']}")
    print(f"{prefix}Eröffnungsbuchungen: {result['openings']}")
    print(f"{prefix}Kontoauszugs-Buchungen: {result['statements']}")


if __name__ == "__main__":
    main()
