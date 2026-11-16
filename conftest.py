import pytest
from django.test import Client

from apps.accounts.models import User
from apps.teams.models import Role, RoleName, Team


@pytest.fixture(autouse=True)
def fast_password_hashing(settings):
    """Cheap hasher: keeps the suite fast. Production still uses Django's default."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture
def make_user(db):
    """Factory: make_user("ana") -> regular user; its password is its username.

    The forced password change is OFF by default so the user can use the app.
    """

    def _make(username="ana", **kwargs):
        kwargs.setdefault("email", f"{username}@example.com")
        kwargs.setdefault("first_name", username.capitalize())
        kwargs.setdefault("last_name", "Test")
        kwargs.setdefault("must_change_password", False)
        return User.objects.create_user(username=username, **kwargs)

    return _make


@pytest.fixture
def sysadmin(db):
    return User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="Admin-pass-1",
        first_name="Root",
        last_name="Admin",
    )


@pytest.fixture
def make_team(db):
    def _make(name="QA Web", **kwargs):
        return Team.objects.create(name=name, **kwargs)

    return _make


@pytest.fixture
def leader_role(db):
    return Role.objects.get(name=RoleName.LEADER)


@pytest.fixture
def tester_role(db):
    return Role.objects.get(name=RoleName.TESTER)


@pytest.fixture
def login():
    """login(user) -> a test client already authenticated as that user."""

    def _login(user):
        client = Client()
        client.force_login(user)
        return client

    return _login


@pytest.fixture
def sysadmin_client(login, sysadmin):
    return login(sysadmin)