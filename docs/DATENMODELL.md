# Datenmodell

Datenbank-Struktur der Bierkasse7: Tabellen, Beziehungen und Konventionen.
Reine ASCII/Unicode-Darstellung – lesbar ohne Mermaid-Renderer. Die Mermaid-
Variante liegt in `docs/DATENMODELL-MERMAID.md`.

> Es gibt **eine** Datenbank (SQLite, portabel auch PostgreSQL). Primärschlüssel
> sind UUID-Strings (`String(36)`), Geldbeträge werden exakt als `Decimal`
> gespeichert (in SQLite als skalierte Ganzzahlen × 10 000). Alle Zeitstempel
> sind UTC.

---

## 1. Überblick nach Gruppen

```
┌─ Identität & Zeit ────────────────────────────────────────────────────┐
│                                                                       │
│   USERS ────1:1──── ACCOUNTS              SEMESTERS                   │
│   (Personen)        (je Person ein        (Zeiträume)                 │
│                      Bestandskonto)                                   │
└───────────────────────────────────────────────────────────────────────┘

┌─ Buchhaltungskern ────────────────────────────────────────────────────┐
│                                                                       │
│   TRANSACTIONS ────1:n──── TRANSACTION_LINES ────n:1── ACCOUNTS       │
│   (Buchungskopf)           (SOLL/HABEN-Zeilen)  ├────n:1── KASSEN-    │
│         │                     │                 │        BEREICHE     │
│         │ self: storno_       └────n:1── USERS (member)               │
│         │ reference_id                                                │
│         └──────────────────────────────────────────────┐             │
│   TRANSACTIONS }───m:n────{ TAGS   (via transaction_tags)            │
│   ACCOUNT_BALANCES ────n:1──── ACCOUNTS / SEMESTERS                   │
│                          (Eröffnungssaldo je Konto+Semester)          │
└───────────────────────────────────────────────────────────────────────┘

┌─ Fachmodule (jedes erzeugt höchstens 1 TRANSACTION) ──────────────────┐
│                                                                       │
│   DELIVERIES ─────1:n──── DELIVERY_ITEMS ────n:1── BEVERAGES          │
│                                                                       │
│   RINGBRETT_SESSIONS ─1:n─ RINGBRETT_ENTRIES ──n:1── USERS            │
│                                                                       │
│   INVENTORIES ────1:n──── INVENTORY_ITEMS ───n:1── BEVERAGES          │
│                                                                       │
│   EVENTS }───m:n────{ TAGS   (via event_tags)                         │
│                                                                       │
│   EXPENSE_REFUND_REQUESTS                                             │
│                                                                       │
│   ──► transaction_id ─────────────────► TRANSACTIONS                  │
│   ──► semester_id / kassenbereich_id ─► SEMESTERS / KASSENBEREICHE    │
└───────────────────────────────────────────────────────────────────────┘

┌─ System ──────────────────────────────────────────────────────────────┐
│   AUDIT_LOGS          NOTIFICATIONS                                   │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 2. Beziehungen (kardinal, mit Fremdschlüssel)

```
USERS      ─1:1─── ACCOUNTS               (accounts.user_id, UNIQUE)
USERS      ─1:n─── TRANSACTIONS           (transactions.created_by_id, approved_by_id)
USERS      ─1:n─── TRANSACTION_LINES      (transaction_lines.member_id)
USERS      ─1:n─── RINGBRETT_ENTRIES       (ringbrett_entries.user_id)
USERS      ─1:n─── EXPENSE_REFUND_REQUESTS (applicant_id, approved_by_id)
USERS      ─1:n─── NOTIFICATIONS          (notifications.user_id)
USERS      ─1:n─── AUDIT_LOGS             (audit_logs.user_id)
USERS      ─1:n─── EVENTS                 (organizer_id, payer_user_id, created_by_id)
USERS      ─1:n─── DELIVERIES             (created_by_id)
USERS      ─1:n─── RINGBRETT_SESSIONS     (counted_by_id)
USERS      ─1:n─── INVENTORIES            (counted_by_id)

SEMESTERS  ─1:n─── TRANSACTIONS           (transactions.semester_id)
SEMESTERS  ─1:n─── ACCOUNT_BALANCES       (account_balances.semester_id)
SEMESTERS  ─1:n─── BEVERAGES              (beverages.semester_id)
SEMESTERS  ─1:n─── DELIVERIES             (deliveries.semester_id)
SEMESTERS  ─1:n─── RINGBRETT_SESSIONS     (ringbrett_sessions.semester_id)
SEMESTERS  ─1:n─── EVENTS                 (events.semester_id)
SEMESTERS  ─1:n─── INVENTORIES            (inventories.semester_id)
SEMESTERS  ─n:1─── USERS                  (semesters.closed_by_id)

ACCOUNTS   ─1:n─── TRANSACTION_LINES      (transaction_lines.account_id)
ACCOUNTS   ─1:n─── ACCOUNT_BALANCES       (account_balances.account_id)
ACCOUNTS   ─1:n─── DELIVERIES             (deliveries.payment_account_id)

KASSENBEREICHE ─1:n─ TRANSACTION_LINES    (transaction_lines.kassenbereich_id)
KASSENBEREICHE ─1:n─ DELIVERIES           (deliveries.kassenbereich_id)
KASSENBEREICHE ─1:n─ RINGBRETT_SESSIONS   (ringbrett_sessions.kassenbereich_id)
KASSENBEREICHE ─1:n─ EVENTS               (events.kassenbereich_id)
KASSENBEREICHE ─1:n─ EXPENSE_REFUND_REQUESTS (expense_refund_requests.kassenbereich_id)

TRANSACTIONS ─1:n─ TRANSACTION_LINES      (transaction_lines.transaction_id)
TRANSACTIONS ─n:1─ TRANSACTIONS           (storno_reference_id, self)
TRANSACTIONS ─1:n─ DELIVERIES             (deliveries.transaction_id)
TRANSACTIONS ─1:n─ RINGBRETT_SESSIONS     (ringbrett_sessions.transaction_id)
TRANSACTIONS ─1:n─ EVENTS                 (events.transaction_id)
TRANSACTIONS ─1:n─ INVENTORIES            (inventories.transaction_id)
TRANSACTIONS ─1:n─ EXPENSE_REFUND_REQUESTS(expense_refund_requests.transaction_id)
TRANSACTIONS ─m:n─ TAGS                   (transaction_tags)

EVENTS     ─1:n─── TRANSACTION_LINES      (transaction_lines.event_id)
EVENTS     ─m:n─── TAGS                   (event_tags)

DELIVERIES ─1:n─── DELIVERY_ITEMS         (delivery_items.delivery_id)
DELIVERY_ITEMS ─n:1─ BEVERAGES            (delivery_items.beverage_id)
INVENTORIES─1:n─── INVENTORY_ITEMS        (inventory_items.inventory_id)
INVENTORY_ITEMS ─n:1─ BEVERAGES           (inventory_items.beverage_id)
RINGBRETT_SESSIONS ─1:n─ RINGBRETT_ENTRIES(ringbrett_entries.session_id)
```

---

## 3. Tabellen-Referenz

Spalten-Legende: `PK` Schlüssel · `FK` Fremdschlüssel → Tabelle · `UK` eindeutig.
Alle Tabellen mit `TimestampMixin` haben zusätzlich `created_at`, `updated_at`.

### users
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| email | String(255) | UK |
| password_hash | String(255) | |
| first_name / last_name | String(100) | |
| membership_status | Enum | |
| system_role | Enum | |
| phone | String(30) | |
| avatar_url | String(500) | |
| iban | String(34) | |
| notes | Text | |
| is_active | Boolean | |
| activated_at / last_login | DateTime | |

### semesters
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| name | String(50) | UK |
| type | Enum | |
| start_date / end_date | Date | |
| status | Enum | |
| closed_at | DateTime | |
| closed_by_id | String(36) | FK → users |

### accounts
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| name | String(100) | |
| type | Enum | |
| user_id | String(36) | FK → users, UK |
| is_active | Boolean | |

### kassenbereiche
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| name | String(100) | UK |
| code | String(40) | UK |
| description | String(300) | |
| is_active | Boolean | |
| sort_order | Integer | |
| opening_balance | Money | |

### tags
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| name | String(80) | UK |
| color | String(20) | |
| description | String(300) | |

### transactions
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| sequential_number | Integer | UK |
| date | Date | |
| description | String(500) | |
| category | Enum | |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| receipt_file | String(500) | |
| receipt_status | Enum | |
| migration_source | String(100) | |
| is_storno / is_locked / is_internal_transfer | Boolean | |
| approval_status | Enum | |
| approved_by_id | String(36) | FK → users |
| approved_at | DateTime | |
| review_note | String(300) | |
| notes | Text | |
| storno_reference_id | String(36) | FK → transactions (self) |
| created_by_id | String(36) | FK → users (NOT NULL) |

### transaction_lines
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| transaction_id | String(36) | FK → transactions (NOT NULL) |
| account_id | String(36) | FK → accounts (NOT NULL) |
| kassenbereich_id | String(36) | FK → kassenbereiche (NOT NULL) |
| member_id | String(36) | FK → users |
| side | Enum (SOLL/HABEN) | |
| amount | Money | |
| description | String(300) | |
| event_id | String(36) | FK → events |

### account_balances
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| account_id | String(36) | FK → accounts (NOT NULL) |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| opening_balance | Money | |
| — | — | UK (account_id, semester_id) |

### beverages
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| name | String(150) | |
| ring_color | Enum | |
| ring_price | Money | |
| bottles_per_crate | Integer | |
| category | String(50) | |
| deposit_per_bottle | Money | |
| is_active | Boolean | |
| semester_id | String(36) | FK → semesters |

### deliveries
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| date | Date | |
| supplier | String(200) | |
| invoice_number | String(100) | |
| invoice_file | String(500) | |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| kassenbereich_id | String(36) | FK → kassenbereiche |
| payment_account_id | String(36) | FK → accounts |
| is_posted | Boolean | |
| transaction_id | String(36) | FK → transactions |
| created_by_id | String(36) | FK → users (NOT NULL) |

### delivery_items
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| delivery_id | String(36) | FK → deliveries (NOT NULL) |
| beverage_id | String(36) | FK → beverages (NOT NULL) |
| crates / single_bottles | Integer | |
| purchase_price / deposit | Money | |

### ringbrett_sessions
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| date | Date | |
| counted_by_id | String(36) | FK → users (NOT NULL) |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| kassenbereich_id | String(36) | FK → kassenbereiche (NOT NULL) |
| zaehlungsnummer | Integer | |
| status | String(20) | |
| notes | Text | |
| transaction_id | String(36) | FK → transactions |

### ringbrett_entries
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| session_id | String(36) | FK → ringbrett_sessions (NOT NULL) |
| user_id | String(36) | FK → users (NOT NULL) |
| red_rings / yellow_rings | Integer | |
| — | — | UK (session_id, user_id) |

### events
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| date | Date | |
| name | String(200) | |
| type | Enum | |
| organizer_id | String(36) | FK → users (NOT NULL) |
| signature | String(100) | |
| payer_type | Enum | |
| payer_user_id | String(36) | FK → users |
| red_glasses / yellow_glasses | Integer | |
| donation | Money | |
| kassenbereich_id | String(36) | FK → kassenbereiche (NOT NULL) |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| is_posted | Boolean | |
| transaction_id | String(36) | FK → transactions |
| created_by_id | String(36) | FK → users (NOT NULL) |

### inventories
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| date | Date | |
| counted_by_id | String(36) | FK → users (NOT NULL) |
| semester_id | String(36) | FK → semesters (NOT NULL) |
| status | String(20) | |
| notes | Text | |
| transaction_id | String(36) | FK → transactions |

### inventory_items
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| inventory_id | String(36) | FK → inventories (NOT NULL) |
| beverage_id | String(36) | FK → beverages (NOT NULL) |
| crates / single_bottles | Integer | |

### expense_refund_requests
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| applicant_id | String(36) | FK → users (NOT NULL) |
| date | Date | |
| amount | Money | |
| description | Text | |
| kassenbereich_id | String(36) | FK → kassenbereiche (NOT NULL) |
| receipt_file | String(500) | |
| status | Enum | |
| approved_by_id | String(36) | FK → users |
| approved_at | DateTime | |
| transaction_id | String(36) | FK → transactions |

### audit_logs
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| user_id | String(36) | FK → users |
| action | Enum | |
| entity_type | String(100) | |
| entity_id | String(36) | |
| old_values / new_values | JSON | |
| description | String(500) | |
| ip_address | String(45) | |
| created_at | DateTime | |

### notifications
| Spalte | Typ | Schlüssel |
|---|---|---|
| id | String(36) | PK |
| user_id | String(36) | FK → users (NOT NULL) |
| type | Enum | |
| subject | String(200) | |
| body | Text | |
| is_read | Boolean | |
| created_at | DateTime | |

### Zwischentabellen (m:n)
| Tabelle | Spalten | ON DELETE |
|---|---|---|
| transaction_tags | transaction_id → transactions, tag_id → tags | CASCADE |
| event_tags | event_id → events, tag_id → tags | CASCADE |

---

## 4. Wichtige Konventionen & Regeln

* **Primärschlüssel:** UUID-Strings (`String(36)`), damit dasselbe Schema auf
  SQLite und PostgreSQL läuft.
* **Geld:** immer `MoneyType` (exaktes `Decimal`, 4 Nachkommastellen, nie
  Float). In SQLite als skalierte Ganzzahl (`× 10 000`).
* **Enums:** als `VARCHAR` gespeichert (`native_enum=False`), Wert = Enum-Wert.
* **Kassenbereich ist Pflicht:** jede `transaction_lines`-Zeile trägt eine
  `kassenbereich_id` – die buchhalterische Dimension.
* **Salden werden berechnet, nicht gespeichert:** gespeichert sind nur
  `kassenbereiche.opening_balance` und `account_balances.opening_balance`
  (Eröffnung); laufende Salden projiziert `balances.py` aus den Zeilen.
* **Freigabe-Workflow:** `transactions.approval_status` (`submitted` →
  `approved` / `rejected`). Nur `approved` zählt in die Salden.
* **Storno:** eine Gegenbuchung mit `is_storno = true` und
  `storno_reference_id` auf die Originalbuchung (kein Löschen).
* **Automatische Buchungen:** Fachmodule (`deliveries`, `events`,
  `ringbrett_sessions`, `inventories`, `expense_refund_requests`) verweisen über
  `transaction_id` auf die von ihnen erzeugte Buchung (`is_posted`-Flag).
* **Kaskaden:** Kind-Zeilen (`delivery_items`, `inventory_items`,
  `ringbrett_entries`) und m:n-Verknüpfungen werden mit dem Elternteil gelöscht
  (`delete-orphan` / `ON DELETE CASCADE`).
* **AuditLog / Notification** haben **kein** `updated_at`, nur `created_at`.
