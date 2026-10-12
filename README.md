# Bierkasse7

Verwaltung einer Verbindungskasse (Bierkasse / CC-Kasse): Buchhaltung mit
Kassenbereichen, Getränke- und Inventurverwaltung, Ringbrett, Veranstaltungen,
Auslagenerstattungen und automatischer Ausstands-Verrechnung per E-Mail.

* **Backend:** Python 3.11, FastAPI, SQLAlchemy 2, Alembic, SQLite
* **Frontend:** React 18, TypeScript, Vite, Tailwind CSS, Zustand
* **Betrieb:** Docker Compose (optional mit eigenem Mailserver via docker-mailserver)

> **Hinweis zu Daten:** Dieses Repository enthält bewusst **keine** echten
> personenbezogenen Daten. Datenbanken, Kontoauszüge, Rechnungen und
> Mailserver-Laufzeitdaten (inkl. DKIM-Schlüsseln) sind per `.gitignore`
> ausgeschlossen. Zugangsdaten und Geheimnisse werden über eine `.env`
> gesteuert, nicht im Code.

---

## Funktionsumfang

| Bereich | Beschreibung |
|---|---|
| **Dashboard** | Salden je Kassenbereich und Kennzahlen |
| **Buchungen** | Buchungen erfassen/bearbeiten, mit Genehmigungsworkflow |
| **Kassenbereiche** | z. B. Bierkasse, CC-Kasse, allgemeiner Bereich |
| **Getränke** | Getränkekatalog mit Ringfarben und Preisen |
| **Inventur** | Bestandsaufnahmen und Schwund |
| **Ringbrett** | Ringbrett-Sitzungen mit Buchungen |
| **Veranstaltungen** | Events und Zuordnung von Kassenbewegungen |
| **Erstattungen** | Einreichen und Bearbeiten von Auslagen |
| **Semester** | Semesterverwaltung (aktiv/geschlossen) |
| **Mitglieder / Profil** | Personen, Rollen und eigene Ausstände |
| **Verrechnung** | Ausstandsübersicht je Person per E-Mail versenden |

---

## Projektstruktur

```
.
├── backend/                 # FastAPI-Anwendung
│   ├── app/
│   │   ├── api/v1/          # REST-Endpunkte (auth, users, transactions, …)
│   │   ├── core/            # Sicherheit (JWT/bcrypt), Geld, Rechte, Fehler
│   │   ├── models/          # SQLAlchemy-Modelle
│   │   ├── schemas/         # Pydantic-Schemas
│   │   ├── services/        # Buchungs-, Salden-, Dashboard-, E-Mail-Logik
│   │   ├── config.py        # Einstellungen (pydantic-settings, Präfix BIERKASSE7_)
│   │   ├── seed.py          # Demo-Daten
│   │   ├── seed_ws2627.py   # Semester/Kassenwarte/Stammdaten
│   │   ├── import_ws26.py   # Import der WS26-Daten (optional)
│   │   └── set_passwords.py # Neue starke Passwörter setzen
│   ├── alembic/             # Migrationen
│   └── tests/               # pytest-Suite
├── frontend/                # React-SPA
│   └── src/features/        # Seiten (Dashboard, Buchungen, …)
├── mailserver/              # optionaler eigener Mailserver (docker-mailserver)
├── data/                    # Laufzeit-Datenbank (SQLite, gitignoriert)
├── docker-compose.yml       # App-Stack (Backend, Frontend, Mailpit)
├── docker-compose.mail.yml  # Zusatz: eigener Mailserver
└── .env.example             # Vorlage für die Konfiguration
```

---

## Schnellstart (Docker Compose)

```bash
cp .env.example .env          # Werte anpassen (mind. SECRET_KEY und Passwörter)
docker compose up -d --build
```

Danach erreichbar unter:

| Dienst | URL |
|---|---|
| Frontend (SPA) | http://localhost:8080 |
| Backend (API) | http://localhost:8000 |
| API-Dokumentation | http://localhost:8000/docs |
| Mailpit (Test-Mails) | http://localhost:8025 |

Beim Start führt der Backend-Container automatisch aus: Migrationen
(`alembic upgrade head`), Stammdaten-Seed (`app.seed_ws2627`) und – falls
vorhanden – den WS26-Import.

Anmeldung mit dem Bootstrap-Konto aus `.env`
(Standard: `admin@example.com` / `change-me` – **bitte ändern**).

---

## Konfiguration

Alle Variablen haben das Präfix `BIERKASSE7_`. Siehe `.env.example`.

| Variable | Beschreibung | Standard |
|---|---|---|
| `BIERKASSE7_SECRET_KEY` | Schlüssel für JWT-Signatur (**in Produktion setzen!**) | unsicherer Dev-Wert |
| `BIERKASSE7_DATABASE_URL` | Datenbank-URL | `sqlite:///./bierkasse7.db` |
| `BIERKASSE7_DEBUG` | Debug-Modus | `true` |
| `BIERKASSE7_BOOTSTRAP_ADMIN_EMAIL` | E-Mail des Bootstrap-Admins | `admin@example.com` |
| `BIERKASSE7_BOOTSTRAP_ADMIN_PASSWORD` | Startpasswort des Admins | `change-me` |
| `BIERKASSE7_BOOTSTRAP_MEMBER_PASSWORD` | Startpasswort für Demo-Mitglieder | `change-me` |
| `BIERKASSE7_SMTP_HOST` | SMTP-Server; leer = Mails nur in `outbox/` | – |
| `BIERKASSE7_SMTP_PORT` / `_USER` / `_PASSWORD` | SMTP-Zugang | – |
| `BIERKASSE7_MAIL_FROM` / `_NAME` | Absender der Verrechnungs-Mails | `verrechnung@example.com` |

---

## Lokale Entwicklung (ohne Docker)

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env        # oder eigene Werte setzen
python -m alembic upgrade head
python -m app.seed_ws2627         # Stammdaten anlegen
python -m uvicorn app.main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (proxied /api -> :8000)
```

---

## Datenbank, Seeds & Migrationen

```bash
cd backend
python -m alembic upgrade head            # Migrationen anwenden
python -m alembic revision -m "..."       # neue Migration erzeugen

python -m app.seed                        # Demo-Daten (Getränke, Mitglieder, …)
python -m app.seed_ws2627                 # Semester + Kassenwarte + Stammdaten
python -m app.import_ws26 --dry-run       # WS26-Import testen (nur anzeigen)
python -m app.import_ws26                 # WS26-Import schreiben (braucht WS26_Data/)
python -m app.set_passwords               # neue starke Passwörter für alle aktiven Personen
```

`app.import_ws26` liest PDF-Dateien aus `WS26_Data/`. Fehlt dieser Ordner
(z. B. in einem frischen Checkout), wird der Import ohne Fehler übersprungen.

---

## Tests

```bash
cd backend
python -m pytest
```

---

## Eigener Mailserver (optional)

Für den Versand der Verrechnungs-Mails über eine eigene Domain statt über den
lokalen Mailpit stehen `docker-compose.mail.yml` und `mailserver/` bereit.
Die vollständige Anleitung inkl. DNS-Records (SPF, DKIM, DMARC) und PTR steht in
[`mailserver/DNS-VORLAGE.md`](mailserver/DNS-VORLAGE.md).

```bash
# .env: MAIL_DOMAIN und MAIL_HOSTNAME setzen
docker compose -f docker-compose.yml -f docker-compose.mail.yml up -d --build
MAIL_FROM_PASSWORD='<sicheres-passwort>' ./mailserver/setup.sh
```

---

## Sicherheit

* In Produktion immer `BIERKASSE7_SECRET_KEY` und alle Startpasswörter setzen.
* `.env` niemals committen (ist bereits in `.gitignore`).
* Passwörter werden ausschließlich als bcrypt-Hash gespeichert.
* Keine echten personenbezogenen Daten oder Zugangsdaten im Repository ablegen.
