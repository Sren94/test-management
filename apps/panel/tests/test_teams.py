import pytest
from django.urls import reverse

from apps.teams.models import Membership, Team

pytestmark = pytest.mark.django_db


# --- Teams ------------------------------------------------------------------
def test_create_team_cleans_extra_spaces(sysadmin_client):
    response = sysadmin_client.post(reverse("panel:team_create"), {"name": "  QA   Web "})
    assert response.status_code == 302
    assert Team.objects.filter(name="QA Web").exists()


def test_create_team_rejects_a_repeated_name_in_any_case(sysadmin_client, make_team):
    make_team("QA Web")
    response = sysadmin_client.post(reverse("panel:team_create"), {"name": "qa web"})
    assert response.status_code == 200
    assert Team.objects.count() == 1


def test_edit_team_can_keep_its_own_name(sysadmin_client, make_team):
    team = make_team("QA Web")
    response = sysadmin_client.post(reverse("panel:team_edit", args=[team.pk]), {"name": "QA Web"})
    assert response.status_code == 302


def test_edit_team_rejects_another_teams_name(sysadmin_client, make_team):
    make_team("QA Web")
    other = make_team("QA Movil")
    response = sysadmin_client.post(reverse("panel:team_edit", args=[other.pk]), {"name": "QA Web"})
    assert response.status_code == 200


def test_toggle_team_keeps_its_memberships(sysadmin_client, make_user, make_team, tester_role):
    team = make_team("QA Web")
    Membership.objects.assign(user=make_user("ana"), team=team, role=tester_role)
    sysadmin_client.post(reverse("panel:team_toggle", args=[team.pk]))
    team.refresh_from_db()
    assert team.is_active is False
    assert Membership.objects.filter(team=team).count() == 1


# --- Members ----------------------------------------------------------------
def test_detail_page_opens(sysadmin_client, make_team):
    team = make_team("QA Web")
    assert sysadmin_client.get(reverse("panel:team_detail", args=[team.pk])).status_code == 200


def test_add_member_with_a_role(sysadmin_client, make_user, make_team, tester_role):
    team, user = make_team("QA Web"), make_user("ana")
    response = sysadmin_client.post(
        reverse("panel:team_detail", args=[team.pk]),
        {"user": user.pk, "role": tester_role.pk},
    )
    assert response.status_code == 302
    membership = Membership.objects.get(user=user, team=team)
    assert membership.role == tester_role


def test_cannot_add_an_admin_or_the_same_person_twice(
    sysadmin_client, sysadmin, make_user, make_team, tester_role
):
    team, user = make_team("QA Web"), make_user("ana")
    url = reverse("panel:team_detail", args=[team.pk])
    sysadmin_client.post(url, {"user": user.pk, "role": tester_role.pk})
    again = sysadmin_client.post(url, {"user": user.pk, "role": tester_role.pk})
    as_admin = sysadmin_client.post(url, {"user": sysadmin.pk, "role": tester_role.pk})
    assert again.status_code == 200
    assert as_admin.status_code == 200
    assert Membership.objects.filter(team=team).count() == 1


def test_changing_a_role_only_affects_that_team(
    sysadmin_client, make_user, make_team, leader_role, tester_role
):
    user = make_user("ana")
    web, mobile = make_team("QA Web"), make_team("QA Movil")
    in_web = Membership.objects.assign(user=user, team=web, role=tester_role)
    in_mobile = Membership.objects.assign(user=user, team=mobile, role=tester_role)
    response = sysadmin_client.post(
        reverse("panel:membership_role", args=[web.pk, in_web.pk]), {"role": leader_role.pk}
    )
    assert response.status_code == 302
    in_web.refresh_from_db()
    in_mobile.refresh_from_db()
    assert in_web.role == leader_role
    assert in_mobile.role == tester_role


def test_invalid_role_changes_nothing(sysadmin_client, make_user, make_team, tester_role):
    team = make_team("QA Web")
    membership = Membership.objects.assign(user=make_user("ana"), team=team, role=tester_role)
    sysadmin_client.post(
        reverse("panel:membership_role", args=[team.pk, membership.pk]), {"role": 99999}
    )
    membership.refresh_from_db()
    assert membership.role == tester_role


def test_removing_a_member_only_affects_that_team(
    sysadmin_client, make_user, make_team, tester_role
):
    user = make_user("ana")
    web, mobile = make_team("QA Web"), make_team("QA Movil")
    in_web = Membership.objects.assign(user=user, team=web, role=tester_role)
    Membership.objects.assign(user=user, team=mobile, role=tester_role)
    sysadmin_client.post(reverse("panel:membership_remove", args=[web.pk, in_web.pk]))
    assert not Membership.objects.filter(team=web).exists()
    assert Membership.objects.filter(team=mobile, user=user).exists()


def test_a_membership_cannot_be_edited_through_another_team(
    sysadmin_client, make_user, make_team, leader_role, tester_role
):
    web, mobile = make_team("QA Web"), make_team("QA Movil")
    membership = Membership.objects.assign(user=make_user("ana"), team=web, role=tester_role)
    change = sysadmin_client.post(
        reverse("panel:membership_role", args=[mobile.pk, membership.pk]),
        {"role": leader_role.pk},
    )
    remove = sysadmin_client.post(reverse("panel:membership_remove", args=[mobile.pk, membership.pk]))
    assert change.status_code == 404
    assert remove.status_code == 404
    membership.refresh_from_db()
    assert membership.role == tester_role