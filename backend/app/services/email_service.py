"""Verrechnungs-E-Mail-Automatismus.

Erzeugt für eine Person eine Aufstellung ihrer **Ausstände** – aufgeschlüsselt
nach Kassenbereich – und versendet sie.

Versand:
* Ist ``smtp_host`` konfiguriert, wird die Mail per SMTP versendet
  (SSL oder STARTTLS).
* Andernfalls wird die Mail als Datei im ``outbox_dir`` abgelegt (Dry-Run),
  damit die Funktion ohne Zugangsdaten testbar bleibt.
"""
from __future__ import annotations

import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.core.money import fmt_eur
from app.models.entities import Kassenbereich, Semester, User
from app.models.enums import SemesterStatus
from app.services import balances


def _active_semester(db: Session) -> Semester | None:
    return db.scalar(select(Semester).where(Semester.status == SemesterStatus.ACTIVE))


def settlement_context(db: Session, user: User, semester_id: str | None = None) -> dict:
    semester = db.get(Semester, semester_id) if semester_id else _active_semester(db)
    by_area = balances.member_balance_by_kassenbereich(db, user.id, semester_id)
    names = {kb.id: kb.name for kb in db.scalars(select(Kassenbereich))}
    rows = [
        {"name": names.get(kb_id, kb_id), "amount": amount}
        for kb_id, amount in by_area.items()
    ]
    rows.sort(key=lambda r: r["name"])
    total = balances.member_total_balance(db, user.id, semester_id)
    return {
        "user": user,
        "semester": semester.name if semester else "aktuelles Semester",
        "rows": rows,
        "total": total,
        "open_amount": total if total > 0 else balances.ZERO,
    }


def render_settlement_email(db: Session, user: User, semester_id: str | None = None) -> dict:
    ctx = settlement_context(db, user, semester_id)
    subject = f"Ausstandsaufstellung {ctx['semester']} – Bierkasse7"
    rows = ctx["rows"]
    lines = [f"Hallo {user.first_name},", ""]
    lines.append(f"deine Ausstände im {ctx['semester']}:")
    lines.append("")
    if rows:
        for row in rows:
            lines.append(f"  • {row['name']}: {fmt_eur(row['amount'])}")
    else:
        lines.append("  • keine Buchungen")
    lines.append("")
    lines.append(f"Gesamt: {fmt_eur(ctx['total'])}")
    lines.append("")
    lines.append("Diese Nachricht wurde automatisch von der Bierkasse7-Verrechnung erzeugt.")
    text = "\n".join(lines)

    row_html = "".join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #E7E3DC;">{r["name"]}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #E7E3DC;text-align:right;'
        f'font-variant-numeric:tabular-nums;">{fmt_eur(r["amount"])}</td></tr>'
        for r in rows
    ) or '<tr><td colspan="2" style="padding:8px 0;color:#6B6862;">keine Buchungen</td></tr>'

    html = f"""\
<!doctype html><html lang="de"><body style="margin:0;background:#FAF9F6;font-family:Inter,Arial,sans-serif;color:#1C1B19;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px;">
<table role="presentation" width="520" cellpadding="0" cellspacing="0" style="background:#FFFFFF;border:1px solid #E7E3DC;border-radius:10px;">
<tr><td style="padding:28px 32px 8px;">
<div style="font-size:12px;letter-spacing:.12em;text-transform:uppercase;color:#6B6862;">Bierkasse7 · Verrechnung</div>
<h1 style="font-size:20px;margin:8px 0 0;">Ausstandsaufstellung {ctx['semester']}</h1>
<p style="color:#6B6862;font-size:14px;margin:8px 0 0;">Hallo {user.first_name}, hier ist die Aufstellung deiner Ausstände.</p>
</td></tr>
<tr><td style="padding:16px 32px 0;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="font-size:14px;">{row_html}
<tr><td style="padding:12px 0;font-weight:600;">Gesamt</td>
<td style="padding:12px 0;text-align:right;font-weight:600;font-variant-numeric:tabular-nums;">{fmt_eur(ctx['total'])}</td></tr>
</table>
</td></tr>
<tr><td style="padding:8px 32px 28px;color:#6B6862;font-size:12px;">
Diese Nachricht wurde automatisch von der Bierkasse7-Verrechnung erzeugt.
</td></tr>
</table></td></tr></table>
</body></html>"""
    return {
        "subject": subject,
        "text": text,
        "html": html,
        "total": ctx["total"],
        "semester": ctx["semester"],
    }


def send_email(to: str, subject: str, text: str, html: str | None = None) -> dict:
    """Versendet die Mail über SMTP oder legt sie im Outbox-Ordner ab."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((settings.mail_from_name, settings.mail_from))
    message["To"] = to
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    if not settings.smtp_host:
        outbox = Path(settings.outbox_dir)
        outbox.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        safe = to.replace("@", "_at_").replace("/", "_")
        path = outbox / f"{stamp}-{safe}.eml"
        path.write_bytes(bytes(message))
        return {
            "delivered": False,
            "transport": "outbox",
            "reason": "SMTP nicht konfiguriert (BIERKASSE7_SMTP_HOST fehlt).",
            "path": str(path.resolve()),
            "to": to,
            "from": settings.mail_from,
            "subject": subject,
        }

    context = ssl.create_default_context()
    if settings.smtp_ssl:
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context, timeout=20)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20)
    try:
        server.ehlo()
        if settings.smtp_starttls and not settings.smtp_ssl:
            server.starttls(context=context)
            server.ehlo()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password or "")
        server.send_message(message)
    finally:
        server.quit()
    return {
        "delivered": True,
        "transport": "smtp",
        "to": to,
        "from": settings.mail_from,
        "subject": subject,
    }


def send_settlement_email(db: Session, user: User, to: str | None = None, semester_id: str | None = None) -> dict:
    rendered = render_settlement_email(db, user, semester_id)
    result = send_email(to or user.email, rendered["subject"], rendered["text"], rendered["html"])
    result["total"] = rendered["total"]
    result["semester"] = rendered["semester"]
    return result
