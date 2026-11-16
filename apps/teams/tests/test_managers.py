import pytest

from apps.teams.models import Membership, Team

pytestmark = pytest.mark.django_db


def names(queryset):
    return sorted(team.name for team in queryset)


# --- Team -------------------------------------------------------------------
def test_team_search_and_status(make_team):
    make_team("QA Web")
    make_team("QA Movil", is_active=False)
    assert names(Team.objects.search("web")) == ["QA Web"]
    assert names(Team.objects.with_status("active")) == ["QA Web"]
    assert names(Team.objects.with_status("inactive")) == ["QA Movil"]
    assert names(Team.objects.with_status("all")) == ["QA Movil", "QA Web"]


def test_team_deactivate_and_activate(make_team):
    team = make_team("QA Web")
    Team.objects.filter(pk=team.pk).deactivate()
    team.refresh_from_db()
    assert team.is_active is False
    Team.objects.filter(pk=team.pk).activate()
    team.refresh_from_db()
    assert team.is_active is True


def test_name_exists_ignores_case_and_can_exclude_itself(make_team):
    team = make_team("QA Web")
    assert Team.objects.name_exists("qa web") is True
    assert Team.objects.name_exists("qa web", exclude_pk=team.pk) is False
    assert Team.objects.name_exists("Other") is False


def test_counts_only_include_active_users(make_user, make_team, leader_role, tester_role):
    team = make_team("QA Web")
    Membership.objects.assign(user=make_user("lead"), team=team, role=leader_role)
    Membership.objects.assign(user=make_user("t1"), team=team, role=tester_role)
    Membership.objects.assign(user=make_user("t2", is_active=False), team=team, role=tester_role)
    counted = Team.objects.with_counts().get(pk=team.pk)
    assert (counted.leaders_count, counted.testers_count) == (1, 1)


# --- Membership -------------------------------------------------------------
def test_active_excludes_inactive_users_and_teams(make_user, make_team, tester_role):
    live_team = make_team("Live")
    dead_team = make_team("Dead", is_active=False)
    user = make_user("ana")
    inactive_user = make_user("off", is_active=False)
    Membership.objects.assign(user=user, team=live_team, role=tester_role)
    Membership.objects.assign(user=user, team=dead_team, role=tester_role)
    Membership.objects.assign(user=inactive_user, team=live_team, role=tester_role)
    active = Membership.objects.active()
    assert [(m.user.username, m.team.name) for m in active] == [("ana", "Live")]


def test_current_is_ordered_by_team_name(make_user, make_team, tester_role):
    user = make_user("ana")
    for name in ("Zeta", "Alfa"):
        Membership.objects.assign(user=user, team=make_team(name), role=tester_role)
    assert [m.team.name for m in user.memberships.current()] == ["Alfa", "Zeta"]


def test_roster_includes_inactive_users_and_lists_leaders_first(
    make_user, make_team, leader_role, tester_role
):
    team = make_team("QA Web")
    Membership.objects.assign(user=make_user("tester"), team=team, role=tester_role)
    Membership.objects.assign(user=make_user("off", is_active=False), team=team, role=tester_role)
    Membership.objects.assign(user=make_user("lead"), team=team, role=leader_role)
    roster = list(Membership.objects.roster(team))
    assert len(roster) == 3
    assert roster[0].role.name == "leader"


def test_set_role_only_changes_the_selected_membership(
    make_user, make_team, leader_role, tester_role
):
    user = make_user("ana")
    first = Membership.objects.assign(user=user, team=make_team("A"), role=tester_role)
    second = Membership.objects.assign(user=user, team=make_team("B"), role=tester_role)
    Membership.objects.filter(pk=first.pk).set_role(leader_role)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.role == leader_role
    assert second.role == tester_role