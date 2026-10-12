# Backend-Architektur

Übersicht, wie die Module zusammenspielen und **wo** Authentifizierung und
Buchungen passieren. Bewusst als reines ASCII/Unicode gehalten – lesbar ohne
Mermaid-Renderer.

Legende: `★` = kritische Stelle („Hauptformel"/„Hauptbuchung").

---

## 1. Schichten & Abhängigkeiten

```
┌───────────────────────────────────────────────────────────────────────┐
│                             Frontend SPA (React)                       │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │  HTTP  /api/v1/...
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ HTTP-Schicht                                  app/api/v1/*.py           │
│                                                                       │
│   auth · transactions · kassenbereiche ·                              │
│   beverages · deliveries · ringbrett · events ·                       │
│   inventory · refunds · accounts · dashboard · users · admin          │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │  Depends(...)
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Auth & Rechte                                 app/api/deps.py          │
│                                                                       │
│   get_current_user  ──►  require_permission(permission)               │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Geschäftslogik                                app/services/*.py        │
│                                                                       │
│   posting_service ──►  ★ accounting_service   (create_transaction)    │
│   (Ringbrett/Event/          │                                        │
│    Lieferung/Erstattung)     ▼                                        │
│                          ★ balances           (Salden/Kontrollgl.)    │
│                                                                       │
│   dashboard_service · email_service ──► balances                      │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Kern                                          app/core/*.py            │
│                                                                       │
│   security (bcrypt + JWT) · permissions (Rolle→Rechte) ·              │
│   money (exakte Decimals) · errors (DomainError)                      │
└───────────────────────────────────┬───────────────────────────────────┘
                                    │
                                    ▼
┌───────────────────────────────────────────────────────────────────────┐
│ Daten                       app/models/entities.py · app/database.py  │
│                                                                       │
│   User · Semester · Account · Kassenbereich · Transaction ·           │
│   TransactionLine · Tag · AuditLog · Beverage · Delivery · …          │
└───────────────────────────────────┬───────────────────────────────────┘
                                    ▼
                              ┌───────────┐
                              │  SQLite   │
                              └───────────┘
```

**Kern-Idee:** Jede Buchung läuft durch **einen** Engpass
(`accounting_service.create_transaction`). Die Feature-Module bauen nur
Buchungszeilen und rufen ihn auf. Salden werden **nirgends gespeichert**,
sondern immer neu aus den Buchungszeilen berechnet (`balances.py`).

---

## 2. Aufruf-Beziehungen (wer ruft wen)

```
auth.py ────────────► core/security (Login/JWT), core/permissions (Rechte)

transactions.py ────► accounting_service  (create/preview/storno/lock/approve/reject)
kassenbereiche.py ──► accounting_service  (internal_transfer)
                  └─► balances            (Kassenbereichsbestand)

beverages.py ───────► posting_service
deliveries.py ──────► posting_service
ringbrett.py ───────► posting_service
events.py ──────────► posting_service
refunds.py ─────────► posting_service

accounts.py ────────► balances            (account_balance)
dashboard.py ───────► dashboard_service ──► balances (control_equation)
users.py ───────────► balances, email_service
admin.py ───────────► email_service

posting_service ────► accounting_service   (immer, nie eine einseitige Zeile)
accounting_service ─► balances (Warnungen/Vorschau), core/money, core/permissions
balances / dashboard_service / email_service ──► models/entities
import_ws26.py ─────► accounting_service   (Eröffnungsbuchungen)
```

---

## 3. Authentifizierung & Rechte

```
Anmeldung
  Frontend ──POST /auth/login {email, pw}──► auth.py
      auth.py ──User per E-Mail laden───────────────► DB
      auth.py ──verify_password (bcrypt)────────────► core/security
      auth.py ──create_access/refresh_token (JWT)───► core/security
      auth.py ──permissions_for(role)───────────────► core/permissions
      auth.py ──Token + Rechte-Liste────────────────► Frontend

Geschützter Request (bei jeder Route)
  Frontend ──GET /… + "Authorization: Bearer <access>"──► auth.py
      auth.py ──decode_token (Signatur + Ablauf)────► core/security
      auth.py ──User aus JWT.sub, is_active?────────► DB
      auth.py ──has_permission(role, Recht)─────────► core/permissions
```

Rollen → Rechte: `core/permissions.py` (`ROLE_PERMISSIONS`, `has_permission`).
Die Routen prüfen **Rechte**, nie direkt Rollen.

---

## 4. Buchung inkl. Freigabe-Workflow

```
Buchung
  transactions.py ──create_transaction(lines, user)──► accounting_service

      1) _validate_lines()      Σ SOLL == Σ HABEN          (★ Invariante)
      2) _resolve_semester()    Datum im Semester?
      3) has_permission(user, BOOKING_APPROVE)?
              ja   → Status APPROVED, is_locked = True
              nein → Status SUBMITTED  (wartet auf Freigabe)
      4) schreiben: Transaction + TransactionLine + AuditLog ──► DB
      5) overdraw_warnings()  ──► balances   (Überziehung?)

    zurück: TransactionResult(warnings)

Freigabe (später, durch Berechtigte)
  transactions.py ──approve() / reject()──► accounting_service
      SUBMITTED → APPROVED   (is_locked = True)

      ⚠  ERST JETZT zählt die Buchung:
         balances._base_stmt filtert approval_status == APPROVED
```

---

## 5. Wo genau was passiert (mit Fundstelle)

| Thema                          | Datei : Zeile                                   | Rolle                                            |
| ------------------------------ | ----------------------------------------------- | ------------------------------------------------ |
| Passwort-Hash (bcrypt)         | `core/security.py:12` / `:16`                   | `hash_password` / `verify_password`              |
| JWT erzeugen/prüfen            | `core/security.py:23`–`46`                      | access-/refresh-Token, `decode_token`            |
| Token → User                   | `api/deps.py:17`                                | `get_current_user`                               |
| Recht erzwingen                | `api/deps.py:32` + `core/permissions.py:69`     | `require_permission` / `has_permission`          |
| Rollen→Rechte-Matrix           | `core/permissions.py:37`                        | `ROLE_PERMISSIONS`                               |
| ★ Hauptbuchung + Invariante    | `services/accounting_service.py:99`             | `create_transaction` (einziger Buchungsweg)      |
| ★ Buchung ausgeglichen?        | `services/accounting_service.py:71`             | `_validate_lines`: **Σ SOLL = Σ HABEN**          |
| Semester-/Datumsprüfung        | `services/accounting_service.py:52`             | `_resolve_semester`                              |
| Freigabe-Workflow              | `accounting_service.py:259` (`approve`), `:275` (`reject`) | Status `ApprovalStatus` (`enums.py:117`) |
| Storno (gespiegelte Buchung)   | `accounting_service.py:216`                     | `stornate`                                       |
| Feature → Buchung              | `services/posting_service.py:66/115/169/211`    | Ringbrett / Event / Lieferung / Erstattung       |
| ★ Hauptformel (Kontrollgl.)    | `services/balances.py:125`                      | `Σ Kassenbereiche = Liquidität + Ford. − Verb.`  |
| Nur freigegebene zählen        | `services/balances.py:47`                       | `_base_stmt` → `approval_status == APPROVED`     |
| Exaktes Geld                   | `core/money.py:21` / `:33`                      | `to_decimal` / `MoneyType` (skalierte Ints)      |
| DB-Session (commit/rollback)   | `database.py:23`                                | `get_db` pro Request                             |
| Audit-Log                      | `accounting_service.py:335`                     | `_audit`                                         |
| E-Mail-Verrechnung             | `services/email_service.py` ↔ `api/v1/users.py:41` | Ausstand je Mitglied                          |

---

## 6. Die zwei „Hauptformeln"

1. **Buchung ausgeglichen** – `accounting_service._validate_lines`
   ```
   Σ SOLL = Σ HABEN        (pro Buchung, mind. 2 Zeilen, Beträge > 0)
   ```

2. **Bestandskontrolle** – `balances.control_equation`
   ```
   Σ Kassenbereichsbestände = Liquidität + Forderungen − Verbindlichkeiten
   ```

Beide beruhen darauf, dass Salden eine **Projektion** der Buchungszeilen sind:
In `TransactionLine` steht nur die Wahrheit (SOLL/HABEN), alles andere wird
abgeleitet. Das sind die kritischen Stellen für Property-Tests oder formale
Verifikation.
