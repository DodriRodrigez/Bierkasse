# Backend-Architektur – Diagramme (Mermaid)

> Diese Datei enthält Mermaid-Diagramme. Sie werden direkt auf GitHub gerendert.
> In Editoren ohne Mermaid-Unterstützung: siehe `docs/ARCHITEKTUR.md`
> (gleicher Inhalt als reine ASCII-Diagramme).

Legende: `★` = kritische Stelle („Hauptformel" / „Hauptbuchung").

---

## 1. Schichten & Abhängigkeiten

```mermaid
flowchart TD
    FE["Frontend SPA (React)"]

    subgraph L1["HTTP-Schicht · app/api/v1/*.py"]
        R_auth["auth"]
        R_tx["transactions"]
        R_kb["kassenbereiche"]
        R_feat["beverages · deliveries · ringbrett<br/>events · inventory · refunds"]
        R_read["accounts · dashboard · users · admin"]
    end

    subgraph L2["Auth & Rechte · app/api/deps.py"]
        DEPS["get_current_user → require_permission"]
    end

    subgraph L3["Geschäftslogik · app/services/*.py"]
        S_post["posting_service<br/>Feature → Buchung"]
        S_acct["accounting_service<br/>create_transaction ⟵ HAUPTBUCHUNG"]
        S_bal["balances<br/>Salden + Kontrollgleichung ⟵ HAUPTFORMEL"]
        S_dash["dashboard_service"]
        S_mail["email_service"]
    end

    subgraph L4["Kern · app/core/*.py"]
        C_sec["security: bcrypt + JWT"]
        C_perm["permissions: Rolle → Rechte"]
        C_money["money: exakte Decimals"]
        C_err["errors: DomainError"]
    end

    subgraph L5["Daten · models + database.py"]
        M["entities: User · Semester · Account ·<br/>Kassenbereich · Transaction · TransactionLine · …"]
        DB[("SQLite")]
    end

    FE --> L1
    R_auth --> DEPS
    R_tx --> DEPS
    R_kb --> DEPS
    R_feat --> DEPS
    R_read --> DEPS
    DEPS --> C_sec
    DEPS --> C_perm

    R_auth --> C_sec
    R_auth --> C_perm
    R_tx --> S_acct
    R_kb --> S_acct
    R_kb --> S_bal
    R_feat --> S_post
    R_read --> S_bal
    R_read --> S_dash
    R_read --> S_mail

    S_post --> S_acct
    S_acct --> S_bal
    S_acct --> C_money
    S_acct --> C_perm
    S_acct --> C_err
    S_post --> C_err
    S_bal --> M
    S_dash --> S_bal
    S_mail --> S_bal
    S_acct --> M
    M --> DB
```

---

## 2. Authentifizierung & Rechte

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant A as auth.py
    participant SEC as core/security
    participant P as core/permissions
    participant DB as SQLite

    FE->>A: POST /auth/login {email, passwort}
    A->>DB: User per E-Mail laden
    A->>SEC: verify_password()  (bcrypt)
    SEC-->>A: ok / nicht ok
    A->>SEC: create_access_token + create_refresh_token (JWT)
    A->>P: permissions_for(role)
    A-->>FE: Token + Rechte-Liste

    Note over FE,DB: Danach bei JEDEM geschützten Request:
    FE->>A: GET /… mit "Authorization: Bearer <access>"
    A->>SEC: decode_token()  (Signatur + Ablauf)
    A->>DB: User aus JWT.sub, is_active?
    A->>P: has_permission(role, benötigtes Recht)
    Note over P: admin/senior/buchhalter/… → Rechtemenge
```

---

## 3. Buchung inkl. Freigabe-Workflow

```mermaid
sequenceDiagram
    participant R as transactions.py
    participant ACC as accounting_service
    participant BAL as balances
    participant DB as SQLite

    R->>ACC: create_transaction(lines, user)
    ACC->>ACC: _validate_lines():  Σ SOLL == Σ HABEN
    ACC->>ACC: _resolve_semester(): Datum im Semester?
    ACC->>ACC: has_permission(user, BOOKING_APPROVE)?
    Note over ACC: berechtigt → APPROVED + is_locked<br/>sonst → SUBMITTED (wartet auf Freigabe)
    ACC->>DB: Transaction + Lines + AuditLog
    ACC->>BAL: overdraw_warnings()  (Überziehung?)
    ACC-->>R: TransactionResult(+warnings)

    Note over R,BAL: Später, durch Berechtigte:
    R->>ACC: approve() / reject()
    ACC->>DB: SUBMITTED → APPROVED (is_locked=True)
    Note over BAL: ERST jetzt zählt die Buchung –<br/>_base_stmt filtert approval_status == APPROVED
```

---

## 4. Wo genau was passiert (mit Fundstelle)

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
