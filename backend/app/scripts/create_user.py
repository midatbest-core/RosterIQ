from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.modules.auth.models import User, UserRole


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a RosterIQ backend user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", choices=[role.value for role in UserRole], default=UserRole.ADMIN.value)
    args = parser.parse_args()

    if len(args.password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")

    email = args.email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise SystemExit(f"A user with email {email} already exists.")
        user = User(
            email=email,
            password_hash=hash_password(args.password),
            role=UserRole(args.role),
        )
        db.add(user)
        db.commit()
        print(f"Created {user.role.value} user {email}")


if __name__ == "__main__":
    main()

