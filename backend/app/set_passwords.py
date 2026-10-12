"""Setzt für alle aktiven Personen neue, starke Passwörter.

Aufruf (im Backend-Container):

    docker compose exec backend python -m app.set_passwords

Es werden kryptografisch zufällige Passwörter erzeugt (4 Blöcke à 4 Zeichen,
ohne verwechselbare Zeichen wie 0/O, 1/l/I) und als bcrypt-Hash gespeichert.
Die Klartext-Passwörter werden einmalig auf der Konsole ausgegeben.
"""
from __future__ import annotations

import secrets

from sqlalchemy import select

from app.core.security import hash_password
from app.database import SessionLocal
from app.models.entities import User

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"


def strong_password() -> str:
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(4))


def main() -> None:
    with SessionLocal() as db:
        users = list(
            db.scalars(
                select(User).where(User.is_active.is_(True)).order_by(User.last_name, User.first_name)
            )
        )
        rows = []
        for user in users:
            password = strong_password()
            user.password_hash = hash_password(password)
            rows.append((user.full_name, user.email, user.system_role.value, password))
        db.commit()

        print("\nNeue Zugangsdaten (bitte sicher verwahren):\n")
        print(f"{'Name':<22}{'E-Mail':<34}{'Rolle':<12}Passwort")
        print("-" * 104)
        for name, email, role, password in rows:
            print(f"{name:<22}{email:<34}{role:<12}{password}")
        print()


if __name__ == "__main__":
    main()
