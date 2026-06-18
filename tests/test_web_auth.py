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


def fake_store():
    from genacademy_rag.core.security import hash_password

    store = FakeDatastore()
    store.admin_hash = hash_password("admin-secret")
    store.member_hash = hash_password("member-secret")
    return store


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
