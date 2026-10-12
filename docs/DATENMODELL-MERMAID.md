# Datenmodell – Diagramm (Mermaid)

> Entity-Relationship-Diagramm der Bierkasse7-Datenbank. Wird direkt auf GitHub
> gerendert. In Editoren ohne Mermaid-Unterstützung: siehe `docs/DATENMODELL.md`
> (gleicher Inhalt als ASCII + Spaltenreferenz).

Legende: `PK` Primärschlüssel · `FK` Fremdschlüssel · `UK` eindeutig.
`||--o{` = 1:0..n · `||--o|` = 1:0..1 · `}o--o{` = m:n.

```mermaid
erDiagram
    USERS {
        string   id PK
        string   email UK
        string   password_hash
        string   first_name
        string   last_name
        string   membership_status
        string   system_role
        string   iban
        bool     is_active
    }

    SEMESTERS {
        string   id PK
        string   name UK
        string   type
        date     start_date
        date     end_date
        string   status
        string   closed_by_id FK
    }

    ACCOUNTS {
        string   id PK
        string   name
        string   type
        string   user_id FK
        bool     is_active
    }

    KASSENBEREICHE {
        string   id PK
        string   name UK
        string   code UK
        decimal  opening_balance
        bool     is_active
    }

    TAGS {
        string   id PK
        string   name UK
        string   color
    }

    TRANSACTIONS {
        string   id PK
        int      sequential_number UK
        date     date
        string   description
        string   category
        string   semester_id FK
        string   approval_status
        bool     is_storno
        bool     is_locked
        string   storno_reference_id FK
        string   created_by_id FK
        string   approved_by_id FK
    }

    TRANSACTION_LINES {
        string   id PK
        string   transaction_id FK
        string   account_id FK
        string   kassenbereich_id FK
        string   member_id FK
        string   event_id FK
        string   side
        decimal  amount
    }

    ACCOUNT_BALANCES {
        string   id PK
        string   account_id FK
        string   semester_id FK
        decimal  opening_balance
    }

    BEVERAGES {
        string   id PK
        string   name
        string   ring_color
        decimal  ring_price
        string   semester_id FK
    }

    DELIVERIES {
        string   id PK
        date     date
        string   supplier
        string   semester_id FK
        string   kassenbereich_id FK
        string   payment_account_id FK
        string   transaction_id FK
        string   created_by_id FK
    }

    DELIVERY_ITEMS {
        string   id PK
        string   delivery_id FK
        string   beverage_id FK
        int      crates
        int      single_bottles
    }

    RINGBRETT_SESSIONS {
        string   id PK
        date     date
        string   counted_by_id FK
        string   semester_id FK
        string   kassenbereich_id FK
        string   transaction_id FK
    }

    RINGBRETT_ENTRIES {
        string   id PK
        string   session_id FK
        string   user_id FK
        int      red_rings
        int      yellow_rings
    }

    EVENTS {
        string   id PK
        date     date
        string   name
        string   type
        string   organizer_id FK
        string   payer_user_id FK
        string   kassenbereich_id FK
        string   semester_id FK
        string   transaction_id FK
    }

    INVENTORIES {
        string   id PK
        date     date
        string   counted_by_id FK
        string   semester_id FK
        string   transaction_id FK
    }

    INVENTORY_ITEMS {
        string   id PK
        string   inventory_id FK
        string   beverage_id FK
        int      crates
        int      single_bottles
    }

    EXPENSE_REFUND_REQUESTS {
        string   id PK
        string   applicant_id FK
        decimal  amount
        string   kassenbereich_id FK
        string   status
        string   transaction_id FK
    }

    AUDIT_LOGS {
        string   id PK
        string   user_id FK
        string   action
        string   entity_type
        string   entity_id
    }

    NOTIFICATIONS {
        string   id PK
        string   user_id FK
        string   type
        string   subject
    }

    USERS        ||--o| ACCOUNTS                 : "hat Bestandskonto"
    USERS        ||--o{ TRANSACTIONS             : "erstellt / gibt frei"
    USERS        ||--o{ TRANSACTION_LINES        : "als member"
    USERS        ||--o{ RINGBRETT_ENTRIES        : "Ringzählung"
    USERS        ||--o{ RINGBRETT_SESSIONS       : "zählt"
    USERS        ||--o{ INVENTORIES              : "zählt"
    USERS        ||--o{ EXPENSE_REFUND_REQUESTS  : "Antrag / Genehmigung"
    USERS        ||--o{ DELIVERIES               : "erstellt"
    USERS        ||--o{ EVENTS                   : "Organisator / Zahler"
    USERS        ||--o{ NOTIFICATIONS            : "erhält"
    USERS        ||--o{ AUDIT_LOGS               : "löst aus"
    USERS        ||--o{ SEMESTERS                : "schließt"

    SEMESTERS    ||--o{ TRANSACTIONS             : "Zeitraum"
    SEMESTERS    ||--o{ ACCOUNT_BALANCES         : "Eröffnung"
    SEMESTERS    ||--o{ BEVERAGES                : "Katalog"
    SEMESTERS    ||--o{ DELIVERIES               : ""
    SEMESTERS    ||--o{ RINGBRETT_SESSIONS       : ""
    SEMESTERS    ||--o{ EVENTS                   : ""
    SEMESTERS    ||--o{ INVENTORIES              : ""

    ACCOUNTS     ||--o{ TRANSACTION_LINES        : "bebucht"
    ACCOUNTS     ||--o{ ACCOUNT_BALANCES         : "Eröffnung"
    ACCOUNTS     ||--o{ DELIVERIES               : "Zahlungskonto"

    KASSENBEREICHE ||--o{ TRANSACTION_LINES      : "Dimension"
    KASSENBEREICHE ||--o{ DELIVERIES             : ""
    KASSENBEREICHE ||--o{ RINGBRETT_SESSIONS     : ""
    KASSENBEREICHE ||--o{ EVENTS                 : ""
    KASSENBEREICHE ||--o{ EXPENSE_REFUND_REQUESTS: ""

    TRANSACTIONS ||--|{ TRANSACTION_LINES        : "besteht aus"
    TRANSACTIONS ||--o{ DELIVERIES               : "verbucht"
    TRANSACTIONS ||--o{ RINGBRETT_SESSIONS       : "verbucht"
    TRANSACTIONS ||--o{ EVENTS                   : "verbucht"
    TRANSACTIONS ||--o{ INVENTORIES              : "verbucht"
    TRANSACTIONS ||--o{ EXPENSE_REFUND_REQUESTS  : "verbucht"
    TRANSACTIONS ||--o| TRANSACTIONS             : "Storno → Original"
    TRANSACTIONS }o--o{ TAGS                     : "transaction_tags"

    EVENTS       ||--o{ TRANSACTION_LINES        : "event_id"
    EVENTS       }o--o{ TAGS                     : "event_tags"

    DELIVERIES   ||--|{ DELIVERY_ITEMS           : ""
    DELIVERY_ITEMS o{--|| BEVERAGES              : "Getränk"
    INVENTORIES  ||--|{ INVENTORY_ITEMS          : ""
    INVENTORY_ITEMS o{--|| BEVERAGES             : "Getränk"
    RINGBRETT_SESSIONS ||--|{ RINGBRETT_ENTRIES  : ""
```

---

## Kern-Erkenntnisse

* **Eine** Datenbank, `TRANSACTIONS` + `TRANSACTION_LINES` sind das Herz:
  jede Zeile hat genau **ein Konto** und **einen Kassenbereich** – daraus
  entstehen alle Salden.
* **Salden werden nicht gespeichert**, nur projiziert. Gespeichert sind nur
  Eröffnungswerte (`KASSENBEREICHE.opening_balance`,
  `ACCOUNT_BALANCES.opening_balance`).
* **Jedes Fachmodul** (`DELIVERIES`, `EVENTS`, `RINGBRETT_SESSIONS`,
  `INVENTORIES`, `EXPENSE_REFUND_REQUESTS`) verweist über `transaction_id` auf
  die von ihm erzeugte Buchung.
* **Storno** = neue Gegenbuchung (`storno_reference_id` → Original), kein Löschen.
* Nur `TRANSACTIONS.approval_status = approved` zählt in die Salden.
