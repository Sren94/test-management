import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

CHANGE_URL = "accounts:password_change"


def test_pending_change_redirects_every_page(login, make_user):
    client = login(make_user("ana", must_change_password=True))
    for name in ("home", "panel:user_list"):
        response = client.get(reverse(name))
        assert response.status_code == 302
        assert response["Location"] == reverse(CHANGE_URL)


def test_change_page_is_reachable_and_warns(login, make_user):
    client = login(make_user("ana", must_change_password=True))
    response = client.get(reverse(CHANGE_URL))
    assert response.status_code == 200
    assert "debes cambiar tu contraseña" in response.content.decode()


def test_logout_is_allowed_while_change_is_pending(login, make_user):
    client = login(make_user("ana", must_change_password=True))
    response = client.post(reverse("accounts:logout"))
    assert response.status_code == 302
    assert response["Location"] == reverse("accounts:login")


def test_changing_the_password_lifts_the_block(login, make_user):
    user = make_user("ana", must_change_password=True)
    client = login(user)
    response = client.post(
        reverse(CHANGE_URL),
        {
            "old_password": "ana",
            "new_password1": "Nueva-clave-2026",
            "new_password2": "Nueva-clave-2026",
        },
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.must_change_password is False
    assert user.check_password("Nueva-clave-2026")
    assert client.get(reverse("home")).status_code == 200


def test_new_password_must_differ_from_the_current_one(login, make_user):
    user = make_user("ana", password="Clave-actual-1", must_change_password=True)
    response = login(user).post(
        reverse(CHANGE_URL),
        {
            "old_password": "Clave-actual-1",
            "new_password1": "Clave-actual-1",
            "new_password2": "Clave-actual-1",
        },
    )
    assert response.status_code == 200
    assert "new_password1" in response.context["form"].errors
    assert User.objects.get(pk=user.pk).must_change_password is True


def test_user_without_pending_change_is_not_blocked(login, make_user):
    client = login(make_user("ana", must_change_password=False))
    assert client.get(reverse("home")).status_code == 200


def test_admin_is_not_blocked(sysadmin_client):
    assert sysadmin_client.get(reverse("panel:user_list")).status_code == 200


def test_anonymous_goes_to_login_not_to_password_change(client):
    response = client.get(reverse("home"))
    assert "/accounts/login/" in response["Location"]