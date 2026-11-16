import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

PAGES = ["panel:user_list", "panel:user_create", "panel:team_list", "panel:team_create"]


@pytest.mark.parametrize("name", PAGES)
def test_anonymous_is_sent_to_login(client, name):
    response = client.get(reverse(name))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


@pytest.mark.parametrize("name", PAGES)
def test_non_admin_gets_403(login, make_user, name):
    assert login(make_user("ana")).get(reverse(name)).status_code == 403


@pytest.mark.parametrize("name", PAGES)
def test_admin_can_open_every_page(sysadmin_client, name):
    assert sysadmin_client.get(reverse(name)).status_code == 200


def test_non_admin_cannot_use_actions(login, make_user, make_team):
    ana, beto, team = make_user("ana"), make_user("beto"), make_team("QA Web")
    client = login(ana)
    urls = [
        reverse("panel:user_toggle", args=[beto.pk]),
        reverse("panel:user_reset_password", args=[beto.pk]),
        reverse("panel:team_toggle", args=[team.pk]),
        reverse("panel:team_detail", args=[team.pk]),
    ]
    for url in urls:
        assert client.post(url).status_code == 403
    assert client.get(reverse("panel:team_detail", args=[team.pk])).status_code == 403
    beto.refresh_from_db()
    team.refresh_from_db()
    assert beto.is_active and team.is_active