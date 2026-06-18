from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from genacademy_rag.core.security import hash_password, verify_password
from genacademy_rag.data.datastore import SQLiteDatastore

from genacademy_coach.settings import CoachSettings

VALID_ROLES = frozenset({"admin", "member"})
DEFAULT_AUTH_MESSAGE = "Sign in with your GenAcademy cohort account."


@dataclass(frozen=True)
class AuthUser:
    email: str
    role: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def auth_enabled_from_env(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip().lower() not in {"0", "false", "no", "off"}


@lru_cache(maxsize=1)
def _dummy_password_hash() -> str:
    return hash_password("not-a-real-genacademy-user")


class CoachAuth:
    def __init__(
        self,
        settings: CoachSettings,
        *,
        datastore: Any | None = None,
        seed_users: bool = True,
    ):
        self._sqlite_path = Path(settings.sqlite_path)
        self.datastore = (
            datastore if datastore is not None else SQLiteDatastore(self._sqlite_path)
        )
        if seed_users:
            self.datastore.seed_users()

    def authenticate(self, email: str, password: str) -> bool:
        return self.user_for_credentials(email, password) is not None

    def user_for_credentials(self, email: str, password: str) -> AuthUser | None:
        row = self.datastore.get_user_by_email(normalize_email(email))
        password_hash = str(row["password"]) if row is not None else _dummy_password_hash()
        password_ok = verify_password(password, password_hash)
        if row is None or not password_ok:
            return None
        role = str(row["role"])
        if role not in VALID_ROLES:
            return None
        return AuthUser(email=str(row["email"]), role=role)

    def get_user(self, email: str | None) -> AuthUser | None:
        if not email:
            return None
        row = self.datastore.get_user_by_email(normalize_email(email))
        if row is None:
            return None
        role = str(row["role"])
        if role not in VALID_ROLES:
            return None
        return AuthUser(email=str(row["email"]), role=role)

    def is_admin(self, email: str | None) -> bool:
        user = self.get_user(email)
        return user is not None and user.role == "admin"

    def create_user(
        self,
        *,
        actor_email: str | None,
        email: str,
        role: str,
        password: str,
    ) -> tuple[bool, str]:
        if not self.is_admin(actor_email):
            return False, "Admin access required."
        clean_email = normalize_email(email)
        clean_role = role.strip().lower()
        if "@" not in clean_email or "." not in clean_email.rsplit("@", 1)[-1]:
            return False, "Enter a valid email address."
        if clean_role not in VALID_ROLES:
            return False, "Role must be admin or member."
        if len(password) < 8:
            return False, "Password must be at least 8 characters."
        created = self.datastore.create_user(
            email=clean_email,
            role=clean_role,
            password_hash=hash_password(password),
        )
        if created is None:
            return False, "A user with that email already exists."
        return True, f"Created {clean_role} account for {clean_email}."

    def list_users(self, *, actor_email: str | None) -> list[dict[str, str]]:
        if not self.is_admin(actor_email):
            return []
        if hasattr(self.datastore, "list_users"):
            return [
                {
                    "email": str(row["email"]),
                    "role": str(row["role"]),
                    "created_at": str(row["created_at"]),
                }
                for row in self.datastore.list_users()
            ]
        with sqlite3.connect(str(self._sqlite_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT email, role, created_at FROM users ORDER BY created_at DESC, email"
            ).fetchall()
        return [
            {
                "email": str(row["email"]),
                "role": str(row["role"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]
