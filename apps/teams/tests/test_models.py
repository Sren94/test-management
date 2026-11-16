import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError

from apps.teams.models import Membership, Role, Team

pytestmark = pytest.mark.django_db


def test_migration_seeds_the_two_roles():
    assert {"leader", "tester"} <= set(Role.objects.values_list("name", flat=True))


def test_role_labels():
    assert Role.objects.get(name="leader").label == "Líder"
    assert Role.objects.get(name="tester").label == "Tester"
    assert Role.objects.create(name="viewer").label == "Viewer"


def test_team_name_is_unique(make_team):
    make_team("QA Web")
    with pytest.raises(IntegrityError), transaction.atomic():
        Team.objects.create(name="QA Web")


def test_membership_is_unique_per_user_and_team(make_user, make_team, leader_role, tester_role):
    user, team = make_user("ana"), make_team("QA Web")
    Membership.objects.assign(user=user, team=team, role=leader_role)
    with pytest.raises(IntegrityError), transaction.atomic():
        Membership.objects.assign(user=user, team=team, role=tester_role)


def test_same_user_can_have_different_roles_in_different_teams(
    make_user, make_team, leader_role, tester_role
):
    user = make_user("ana")
    web, mobile = make_team("QA Web"), make_team("QA Movil")
    Membership.objects.assign(user=user, team=web, role=leader_role)
    Membership.objects.assign(user=user, team=mobile, role=tester_role)
    roles = {m.team.name: m.role.name for m in user.memberships.select_related("team", "role")}
    assert roles == {"QA Web": "leader", "QA Movil": "tester"}


def test_things_with_memberships_cannot_be_deleted(
    make_user, make_team, tester_role
):
    user, team = make_user("ana"), make_team("QA Web")
    Membership.objects.assign(user=user, team=team, role=tester_role)
    with pytest.raises(ProtectedError):
        user.delete()
    with pytest.raises(ProtectedError):
        team.delete()
    with pytest.raises(ProtectedError):
        tester_role.delete()