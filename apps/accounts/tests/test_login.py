import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_login_with_valid_credentials(client, make_user):
    make_user("ana")
    response = client.post(reverse("accounts:login"), {"username": "ana", "password": "ana"})
    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert "_auth_user_id" in client.session


def test_login_with_wrong_password_fails(client, make_user):
    make_user("ana")
    response = client.post(reverse("accounts:login"), {"username": "ana", "password": "nope"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_inactive_user_cannot_login(client, make_user):
    make_user("ana", is_active=False)
    response = client.post(reverse("accounts:login"), {"username": "ana", "password": "ana"})
    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


def test_logged_user_is_sent_away_from_login(login, make_user):
    response = login(make_user("ana")).get(reverse("accounts:login"))
    assert response.status_code == 302


def test_home_requires_login(client):
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_home_loads_for_a_logged_user(login, make_user):
    assert login(make_user("ana")).get(reverse("home")).status_code == 200