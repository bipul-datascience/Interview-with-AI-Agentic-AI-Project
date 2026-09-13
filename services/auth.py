"""Password authentication backed by the application database."""

from __future__ import annotations

import bcrypt
from sqlalchemy import select

from services.database import User, session_scope


def register_user(email: str, password: str) -> User:
    email = email.strip().lower()
    if "@" not in email or len(email) > 320:
        raise ValueError("Enter a valid email address.")
    if len(password) < 10:
        raise ValueError("Use a password with at least 10 characters.")
    with session_scope() as db:
        if db.scalar(select(User).where(User.email == email)):
            raise ValueError("An account with this email already exists.")
        user = User(email=email, password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())
        db.add(user)
        db.flush()
        return user


def authenticate_user(email: str, password: str) -> User | None:
    with session_scope() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if user and bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            return user
    return None
