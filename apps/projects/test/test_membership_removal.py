import pytest
from django.urls import reverse

from apps.projects.models import Project, ProjectAssignment
from apps.teams.models import Membership

pytestmark = pytest.mark.django_db


def membership_of(user, team):
    return Membership.objects.get(user=user, team=team)


def current_users(project):
    current = ProjectAssignment.objects.current().filter(project=project)
    return sorted(a.user.username for a in current)


def test_remove_deletes_the_membership_and_closes_the_assignment(scenario):
    closed = Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    assert closed == 1
    assert not Membership.objects.filter(user=scenario.tester_in, team=scenario.web).exists()
    assert current_users(scenario.p_web) == []


def test_the_closed_assignment_stays_in_the_history(scenario):
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    history = ProjectAssignment.objects.closed().filter(project=scenario.p_web)
    assert [a.user.username for a in history] == ["tester_in"]
    assert history[0].removed_at is not None


def test_assignments_in_other_teams_are_untouched(scenario, tester_role, assign_to_project):
    Membership.objects.assign(user=scenario.tester_in, team=scenario.mobile, role=tester_role)
    assign_to_project(scenario.p_mobile, scenario.tester_in)
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    assert current_users(scenario.p_web) == []
    assert current_users(scenario.p_mobile) == ["tester_in", "tester_mobile"]


def test_other_peoples_assignments_are_untouched(scenario, assign_to_project):
    assign_to_project(scenario.p_web, scenario.lead_web)
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    assert current_users(scenario.p_web) == ["lead_web"]


def test_removing_someone_without_assignments_closes_nothing(scenario):
    assert Membership.objects.remove(membership_of(scenario.tester_out, scenario.web)) == 0
    assert current_users(scenario.p_web) == ["tester_in"]


def test_the_person_loses_every_permission_over_the_team_projects(scenario):
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    assert list(Project.objects.visible_to(scenario.tester_in)) == []
    assert list(Project.objects.manageable_by(scenario.tester_in)) == []


def test_a_leader_who_leaves_loses_the_team_projects_too(scenario):
    Membership.objects.remove(membership_of(scenario.lead_web, scenario.web))
    assert list(Project.objects.manageable_by(scenario.lead_web)) == []


def test_coming_back_to_the_team_does_not_restore_the_assignment(scenario, tester_role):
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    Membership.objects.assign(user=scenario.tester_in, team=scenario.web, role=tester_role)
    assert current_users(scenario.p_web) == []
    assert list(Project.objects.manageable_by(scenario.tester_in)) == []
    assert ProjectAssignment.objects.assign(project=scenario.p_web, user=scenario.tester_in)
    assert ProjectAssignment.objects.filter(project=scenario.p_web, user=scenario.tester_in).count() == 2


def test_archived_projects_also_have_their_assignments_closed(scenario):
    Project.objects.filter(pk=scenario.p_web.pk).archive()
    Membership.objects.remove(membership_of(scenario.tester_in, scenario.web))
    assert current_users(scenario.p_web) == []


# --- through the panel ------------------------------------------------------
def remove_url(team, membership):
    return reverse("panel:membership_remove", args=[team.pk, membership.pk])


def test_the_panel_removal_closes_assignments_and_says_so(sysadmin_client, scenario):
    membership = membership_of(scenario.tester_in, scenario.web)
    response = sysadmin_client.post(remove_url(scenario.web, membership), follow=True)
    assert current_users(scenario.p_web) == []
    text = " ".join(str(m) for m in response.context["messages"])
    assert "Se cerraron 1 asignación" in text


def test_the_panel_message_stays_short_when_nothing_was_closed(sysadmin_client, scenario):
    membership = membership_of(scenario.tester_out, scenario.web)
    response = sysadmin_client.post(remove_url(scenario.web, membership), follow=True)
    text = " ".join(str(m) for m in response.context["messages"])
    assert "fue quitado" in text
    assert "Se cerraron" not in text


def test_non_admins_cannot_remove_people_from_a_team(login, scenario):
    membership = membership_of(scenario.tester_in, scenario.web)
    assert login(scenario.lead_web).post(remove_url(scenario.web, membership)).status_code == 403
    assert Membership.objects.filter(pk=membership.pk).exists()
    assert current_users(scenario.p_web) == ["tester_in"]
    