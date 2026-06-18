from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from genacademy_rag.core.security import hash_password, verify_password
from genacademy_rag.data.datastore import SQLiteDatastore

from genacademy_coach.settings import CoachSettings

VALID_ROLES = frozenset({"admin", "member"})
DEFAULT_AUTH_MESSAGE = """
<section style="margin: 0 0 18px; text-align: left;">
  <p style="
    margin: 0 0 6px;
    color: #66706b;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.14em;
    text-transform: uppercase;
  ">
    Adaptive grounded tutor
  </p>
  <h1 style="
    margin: 0 0 8px;
    color: #202629;
    font-family: Georgia, Cambria, &quot;Times New Roman&quot;, Times, serif;
    font-size: 32px !important;
    line-height: 1.05 !important;
  ">
    GenAcademy Coach
  </h1>
  <p style="
    margin: 0 0 12px;
    color: #4f5b55;
    font-size: 14px;
    line-height: 1.45;
  ">
    Sign in with your cohort account to access cited tutoring,
    deterministic quizzes, and scoped learner memory.
  </p>
  <p style="
    margin: 0;
    color: #314f37;
    font-size: 12px;
    font-weight: 700;
  ">
    Course-grounded answers &middot; Redacted traces &middot; Salted learner state
  </p>
</section>
"""


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
            self._enforce_seed_password_overrides()

    def authenticate(self, email: str, password: str) -> bool:
        return self.user_for_credentials(email, password) is not None

    def _enforce_seed_password_overrides(self) -> None:
        seeds = (
            ("admin@genacademy.local", "GENACADEMY_SEED_ADMIN_PASSWORD"),
            ("member@genacademy.local", "GENACADEMY_SEED_MEMBER_PASSWORD"),
        )
        overrides = [
            (email, password)
            for email, env_name in seeds
            if (password := os.environ.get(env_name))
        ]
        if not overrides:
            return
        try:
            with sqlite3.connect(str(self._sqlite_path)) as conn:
                conn.executemany(
                    "UPDATE users SET password=? WHERE email=?",
                    [(hash_password(password), email) for email, password in overrides],
                )
        except sqlite3.Error:
            return

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
