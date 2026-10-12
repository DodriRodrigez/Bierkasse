#!/bin/sh
set -e

echo "[bierkasse7] Migrationen anwenden …"
python -m alembic upgrade head

echo "[bierkasse7] Datenbestand WS 26/27 sicherstellen …"
python -m app.seed_ws2627

echo "[bierkasse7] WS26-Daten importieren …"
python -m app.import_ws26

echo "[bierkasse7] Server starten …"
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
