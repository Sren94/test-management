import pytest
from django.db import transaction

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_create_user_uses_username_as_initial_password():
    user = User.objects.create_user(
        username="ana", email="Ana@Example.com", first_name="Ana", last_name="Lopez"
    )
    assert user.check_password("ana")
    assert user.must_change_password is True
    assert (user.is_staff, user.is_superuser) == (False, False)
    assert user.email == "ana@example.com"


def test_create_user_requires_all_data():
    with pytest.raises(ValueError):
        User.objects.create_user(
            username="ana", email="ana@example.com", first_name="", last_name="Lopez"
        )


def test_create_superuser_sets_admin_flags():
    admin = User.objects.create_superuser(
        username="root",
        email="root@example.com",
        password="Admin-pass-1",
        first_name="Root",
        last_name="Admin",
    )
    assert admin.is_superuser and admin.is_staff and admin.is_admin
    assert admin.must_change_password is False


def test_create_superuser_requires_a_password():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password=None,
            first_name="Root",
            last_name="Admin",
        )


def test_create_superuser_requires_names():
    with pytest.raises(ValueError):
        User.objects.create_superuser(
            username="root", email="root@example.com", password="Admin-pass-1"
        )




def test_is_staff_always_follows_is_superuser(make_user):
    user = make_user("ana")
    user.is_superuser = True
    user.save()
    assert user.is_staff is True
    user.is_superuser = False
    user.save()
    assert user.is_staff is False


def test_regular_user_is_not_admin(make_user):
    assert make_user("ana").is_admin is False
    
def test_email_can_be_shared_between_users(make_user):
    make_user("one")
    make_user("two", email="one@example.com")
    assert User.objects.filter(email="one@example.com").count() == 2