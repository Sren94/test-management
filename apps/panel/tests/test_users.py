import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

DATA = {
    "username": "prueba",
    "first_name": "Pru",
    "last_name": "Eba",
    "email": "Prueba@Example.com",
}


def test_create_user(sysadmin_client):
    response = sysadmin_client.post(reverse("panel:user_create"), DATA)
    assert response.status_code == 302
    user = User.objects.get(username="prueba")
    assert user.check_password("prueba")
    assert user.must_change_password is True
    assert user.email == "prueba@example.com"
    assert not user.memberships.exists()


def test_create_user_allows_an_email_already_used_by_another_user(sysadmin_client, make_user):
    make_user("existing", email="prueba@example.com")
    response = sysadmin_client.post(
        reverse("panel:user_create"), {**DATA, "email": "PRUEBA@EXAMPLE.COM"}
    )
    assert response.status_code == 302
    assert User.objects.filter(email="prueba@example.com").count() == 2


def test_create_user_rejects_usernames_with_spaces(sysadmin_client):
    response = sysadmin_client.post(
        reverse("panel:user_create"), {**DATA, "username": "Luis Rene"}
    )
    assert response.status_code == 200
    assert not User.objects.filter(first_name="Pru").exists()


def test_edit_user_changes_data_but_not_the_username(sysadmin_client, make_user):
    user = make_user("ana")
    response = sysadmin_client.post(
        reverse("panel:user_edit", args=[user.pk]),
        {"first_name": "Anita", "last_name": "Nueva", "email": "nueva@example.com"},
    )
    assert response.status_code == 302
    user.refresh_from_db()
    assert (user.username, user.first_name, user.email) == ("ana", "Anita", "nueva@example.com")


def test_toggle_deactivates_and_reactivates(sysadmin_client, make_user):
    user = make_user("ana")
    url = reverse("panel:user_toggle", args=[user.pk])
    sysadmin_client.post(url)
    user.refresh_from_db()
    assert user.is_active is False
    sysadmin_client.post(url)
    user.refresh_from_db()
    assert user.is_active is True


def test_admin_cannot_deactivate_themselves(sysadmin_client, sysadmin):
    sysadmin_client.post(reverse("panel:user_toggle", args=[sysadmin.pk]))
    sysadmin.refresh_from_db()
    assert sysadmin.is_active is True


def test_reset_password_shows_a_temporary_password_once(sysadmin_client, make_user):
    user = make_user("ana")
    response = sysadmin_client.post(reverse("panel:user_reset_password", args=[user.pk]))
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    temp = response.context["temp_password"]
    user.refresh_from_db()
    assert len(temp) == 10
    assert user.check_password(temp)
    assert not user.check_password("ana")
    assert user.must_change_password is True


def test_reset_password_needs_post(sysadmin_client, make_user):
    user = make_user("ana")
    assert sysadmin_client.get(reverse("panel:user_reset_password", args=[user.pk])).status_code == 405


def test_reset_password_is_blocked_for_self_and_inactive_users(
    sysadmin_client, sysadmin, make_user
):
    inactive = make_user("off", is_active=False)
    for target in (sysadmin, inactive):
        response = sysadmin_client.post(reverse("panel:user_reset_password", args=[target.pk]))
        assert response.status_code == 302
    sysadmin.refresh_from_db()
    inactive.refresh_from_db()
    assert sysadmin.check_password("Admin-pass-1")
    assert inactive.check_password("off")


def test_user_list_search(sysadmin_client, make_user):
    make_user("ana")
    make_user("beto")
    response = sysadmin_client.get(reverse("panel:user_list"), {"q": "ana"})
    assert [u.username for u in response.context["users"]] == ["ana"]