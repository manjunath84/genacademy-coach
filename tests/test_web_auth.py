import sqlite3
from types import SimpleNamespace

from genacademy_coach.web.auth import CoachAuth, auth_enabled_from_env, normalize_email


class FakeDatastore:
    def __init__(self):
        self.users = {}
        self.seeded = False

    def seed_users(self):
        self.seeded = True
        self.users.setdefault(
            "admin@genacademy.local",
            {
                "email": "admin@genacademy.local",
                "role": "admin",
                "password": self.admin_hash,
                "created_at": "2026-06-18 00:00:00",
            },
        )
        self.users.setdefault(
            "member@genacademy.local",
            {
                "email": "member@genacademy.local",
                "role": "member",
                "password": self.member_hash,
                "created_at": "2026-06-18 00:00:00",
            },
        )

    def get_user_by_email(self, email):
        return self.users.get(email)

    def create_user(self, *, email, role, password_hash):
        if email in self.users:
            return None
        self.users[email] = {
            "email": email,
            "role": role,
            "password": password_hash,
            "created_at": "2026-06-18 00:00:00",
        }
        return self.users[email]

    def list_users(self):
        return sorted(self.users.values(), key=lambda row: (row["created_at"], row["email"]))


def fake_store():
    from genacademy_rag.core.security import hash_password

    store = FakeDatastore()
    store.admin_hash = hash_password("admin-secret")
    store.member_hash = hash_password("member-secret")
    return store


class StaleSeedSQLiteDatastore:
    def __init__(self, path):
        self.path = path
        with sqlite3.connect(str(path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('admin','member')),
                    password TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def seed_users(self):
        from genacademy_rag.core.security import hash_password

        with sqlite3.connect(str(self.path)) as conn:
            conn.executemany(
                "INSERT OR IGNORE INTO users(email, role, password) VALUES (?,?,?)",
                [
                    ("admin@genacademy.local", "admin", hash_password("admin")),
                    ("member@genacademy.local", "member", hash_password("member")),
                ],
            )

    def get_user_by_email(self, email):
        with sqlite3.connect(str(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        return dict(row) if row else None

    def create_user(self, *, email, role, password_hash):
        with sqlite3.connect(str(self.path)) as conn:
            try:
                conn.execute(
                    "INSERT INTO users(email, role, password) VALUES (?,?,?)",
                    (email, role, password_hash),
                )
            except sqlite3.IntegrityError:
                return None
        return self.get_user_by_email(email)

    def list_users(self):
        with sqlite3.connect(str(self.path)) as conn:
            conn.row_factory = sqlite3.Row
            return [
                dict(row)
                for row in conn.execute(
                    "SELECT email, role, created_at FROM users ORDER BY created_at, email"
                ).fetchall()
            ]


def test_auth_enabled_default_and_opt_out_values():
    assert auth_enabled_from_env(None) is True
    assert auth_enabled_from_env("true") is True
    assert auth_enabled_from_env("false") is False
    assert auth_enabled_from_env("0") is False
    assert auth_enabled_from_env("off") is False


def test_coach_auth_reuses_seeded_rag_users_and_normalizes_email():
    store = fake_store()
    auth = CoachAuth(SimpleNamespace(sqlite_path="unused"), datastore=store)

    assert store.seeded is True
    assert normalize_email(" Admin@GenAcademy.Local ") == "admin@genacademy.local"
    assert auth.authenticate(" Admin@GenAcademy.Local ", "admin-secret") is True
    assert auth.authenticate("member@genacademy.local", "member-secret") is True
    assert auth.authenticate("member@genacademy.local", "wrong") is False
    assert auth.get_user("ADMIN@GENACADEMY.LOCAL").role == "admin"


def test_coach_auth_enforces_seed_password_overrides_for_existing_space_users(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GENACADEMY_SEED_ADMIN_PASSWORD", "rotated-admin-secret")
    monkeypatch.setenv("GENACADEMY_SEED_MEMBER_PASSWORD", "rotated-member-secret")
    sqlite_path = tmp_path / "coach.sqlite"
    store = StaleSeedSQLiteDatastore(sqlite_path)

    auth = CoachAuth(SimpleNamespace(sqlite_path=sqlite_path), datastore=store)

    assert auth.authenticate("admin@genacademy.local", "rotated-admin-secret") is True
    assert auth.authenticate("member@genacademy.local", "rotated-member-secret") is True
    assert auth.authenticate("admin@genacademy.local", "admin") is False
    assert auth.authenticate("member@genacademy.local", "member") is False


def test_admin_can_create_users_but_member_cannot():
    store = fake_store()
    auth = CoachAuth(SimpleNamespace(sqlite_path="unused"), datastore=store)

    ok, message = auth.create_user(
        actor_email="member@genacademy.local",
        email="learner@example.com",
        role="member",
        password="learner-secret",
    )

    assert ok is False
    assert message == "Admin access required."

    ok, message = auth.create_user(
        actor_email="admin@genacademy.local",
        email="Learner@Example.com",
        role="member",
        password="learner-secret",
    )

    assert ok is True
    assert "learner@example.com" in message
    assert auth.authenticate("learner@example.com", "learner-secret") is True
    assert auth.list_users(actor_email="member@genacademy.local") == []
    assert [row["email"] for row in auth.list_users(actor_email="admin@genacademy.local")] == [
        "admin@genacademy.local",
        "learner@example.com",
        "member@genacademy.local",
    ]
