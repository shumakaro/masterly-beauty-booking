"""Provision ADMIN explicitly; no self-registration or default credentials."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User
from app.db.session import get_engine
from app.schemas.auth import Registration


def main():
    parser = argparse.ArgumentParser(description="Create a MASTERLY administrator")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    password = getpass("Admin password: ")
    if password != getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")
    try:
        data = Registration(email=args.email, display_name=args.name, password=password)
    except ValidationError:
        raise SystemExit(
            "Invalid email/name/password; password must be 10+ characters and <=72 UTF-8 bytes"
        ) from None
    email = str(data.email).lower()
    with Session(get_engine()) as db, db.begin():
        if db.scalar(select(User.id).where(User.email == email)):
            raise SystemExit("Email already exists; no account was changed")
        db.add(
            User(
                email=email,
                display_name=data.display_name,
                role="ADMIN",
                password_hash=hash_password(password),
            )
        )
    print("Administrator created. Password was not saved in source or logs.")


if __name__ == "__main__":
    main()
