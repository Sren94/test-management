import pytest
from django.utils import timezone

from apps.projects.models import Project, ProjectAssignment
from apps.teams.models import Membership, Team

pytestmark = pytest.mark.django_db


def names(queryset):
    return sorted(project.name for project in queryset)


# --- visible_to -------------------------------------------------------------
def test_everyone_in_a_team_sees_its_projects(scenario):
    for user in (scenario.lead_web, scenario.tester_in, scenario.tester_out):
        assert names(Project.objects.visible_to(user)) == ["Proyecto Web"]


def test_nobody_sees_projects_of_other_teams(scenario):
    assert names(Project.objects.visible_to(scenario.tester_mobile)) == ["Proyecto Movil"]
    assert names(Project.objects.visible_to(scenario.nobody)) == []


def test_admin_sees_everything(scenario, sysadmin):
    assert names(Project.objects.visible_to(sysadmin)) == ["Proyecto Movil", "Proyecto Web"]


def test_a_project_is_never_repeated(scenario):
    # tester_in is a member AND assigned: still one row
    assert len(list(Project.objects.visible_to(scenario.tester_in))) == 1


def test_projects_of_inactive_teams_are_hidden_except_for_admin(scenario, sysadmin):
    Team.objects.filter(pk=scenario.web.pk).deactivate()
    assert names(Project.objects.visible_to(scenario.lead_web)) == []
    assert "Proyecto Web" in names(Project.objects.visible_to(sysadmin))


def test_archived_projects_are_still_visible_but_separable(scenario):
    Project.objects.filter(pk=scenario.p_web.pk).update(is_active=False)
    visible = Project.objects.visible_to(scenario.tester_out)
    assert names(visible) == ["Proyecto Web"]
    assert names(visible.active()) == []
    assert names(visible.archived()) == ["Proyecto Web"]


# --- manageable_by ----------------------------------------------------------
def test_leader_manages_every_project_of_the_team(scenario):
    assert names(Project.objects.manageable_by(scenario.lead_web)) == ["Proyecto Web"]


def test_assigned_tester_manages_their_project(scenario):
    assert names(Project.objects.manageable_by(scenario.tester_in)) == ["Proyecto Web"]


def test_unassigned_tester_can_only_view(scenario):
    assert names(Project.objects.visible_to(scenario.tester_out)) == ["Proyecto Web"]
    assert names(Project.objects.manageable_by(scenario.tester_out)) == []


def test_a_closed_assignment_removes_the_permission(scenario):
    ProjectAssignment.objects.filter(project=scenario.p_web, user=scenario.tester_in).update(
        removed_at=timezone.now()
    )
    assert names(Project.objects.manageable_by(scenario.tester_in)) == []
    assert names(Project.objects.visible_to(scenario.tester_in)) == ["Proyecto Web"]


def test_leader_manages_only_the_teams_where_they_lead(scenario, tester_role):
    Membership.objects.assign(user=scenario.lead_web, team=scenario.mobile, role=tester_role)
    assert names(Project.objects.visible_to(scenario.lead_web)) == [
        "Proyecto Movil",
        "Proyecto Web",
    ]
    assert names(Project.objects.manageable_by(scenario.lead_web)) == ["Proyecto Web"]


def test_users_of_other_teams_and_without_team_manage_nothing(scenario):
    assert names(Project.objects.manageable_by(scenario.tester_mobile)) == ["Proyecto Movil"]
    assert names(Project.objects.manageable_by(scenario.nobody)) == []


def test_admin_manages_everything(scenario, sysadmin):
    assert names(Project.objects.manageable_by(sysadmin)) == ["Proyecto Movil", "Proyecto Web"]