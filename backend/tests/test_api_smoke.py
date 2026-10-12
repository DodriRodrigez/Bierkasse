"""End-to-end API smoke test through the FastAPI TestClient."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_api_smoke(db, world):
    db.commit()  # make the seeded world visible to other sessions
    client = TestClient(app)

    # unauthenticated access is rejected
    assert client.get("/api/v1/dashboard/summary").status_code == 401

    # login
    resp = client.post("/api/v1/auth/login", json={"email": "admin@testverbindung.de", "password": "admin123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # identity
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["system_role"] == "admin"

    # master data
    areas = client.get("/api/v1/kassenbereiche", headers=headers)
    assert areas.status_code == 200
    assert len(areas.json()) == 3

    kb = world.kb["CC"].id
    online = world.account("Onlinekonto").id
    expense = world.account("Aufwand").id

    # balanced booking
    payload = {
        "date": "2026-11-01",
        "description": "Smoke Buchung",
        "category": "MISC",
        "semester_id": world.semester.id,
        "lines": [
            {"account_id": expense, "side": "SOLL", "amount": 25.5, "kassenbereich_id": kb},
            {"account_id": online, "side": "HABEN", "amount": 25.5, "kassenbereich_id": kb},
        ],
        "tags": ["Konvent"],
    }
    created = client.post("/api/v1/transactions", json=payload, headers=headers)
    assert created.status_code == 201, created.text
    assert created.json()["lines"][0]["amount"] == 25.5

    # unbalanced booking is rejected with 422
    bad = dict(payload, lines=[dict(payload["lines"][0], amount=10), dict(payload["lines"][1], amount=9)])
    assert client.post("/api/v1/transactions", json=bad, headers=headers).status_code == 422

    # Buchungsvorschau (Regression: Feldname "date" darf den Typ nicht überschatten)
    preview = client.post(
        "/api/v1/transactions/preview",
        json={"date": "2026-11-01", "lines": payload["lines"]},
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert "areas" in preview.json()

    # dashboard reflects the booking
    summary = client.get("/api/v1/dashboard/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["control_equation"]["balanced"] is True
