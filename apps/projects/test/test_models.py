import pytest
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.projects.models import Project, ProjectAssignment

pytestmark = pytest.mark.django_db


def test_folio_can_repeat(make_team, make_project):
    team = make_team("QA Web")
    make_project(team, "Uno", "SISAP-1")
    make_project(team, "Dos", "SISAP-1")
    assert Project.objects.filter(sisap_folio="SISAP-1").count() == 2


def test_only_one_current_assignment_per_user_and_project(
    make_user, make_team, make_project, assign_to_project
):
    project, user = make_project(make_team("QA Web")), make_user("ana")
    assign_to_project(project, user)
    with pytest.raises(IntegrityError), transaction.atomic():
        assign_to_project(project, user)


def test_reassigning_after_removal_keeps_the_history(
    make_user, make_team, make_project, assign_to_project
):
    project, user = make_project(make_team("QA Web")), make_user("ana")
    first = assign_to_project(project, user)
    ProjectAssignment.objects.filter(pk=first.pk).update(removed_at=timezone.now())
    assign_to_project(project, user)
    assert ProjectAssignment.objects.filter(project=project, user=user).count() == 2
    assert ProjectAssignment.objects.current().filter(project=project, user=user).count() == 1


def test_a_team_with_projects_cannot_be_deleted(make_team, make_project):
    team = make_team("QA Web")
    make_project(team)
    with pytest.raises(ProtectedError):
        team.delete()


def test_a_user_with_assignments_cannot_be_deleted(
    make_user, make_team, make_project, assign_to_project
):
    user = make_user("ana")
    assign_to_project(make_project(make_team("QA Web")), user)
    with pytest.raises(ProtectedError):
        user.delete()


def test_creator_is_cleared_if_the_user_is_deleted(make_user, make_team, make_project):
    creator = make_user("ana")
    project = make_project(make_team("QA Web"), created_by=creator)
    creator.delete()
    project.refresh_from_db()
    assert project.created_by is None


def test_active_and_archived(make_team, make_project):
    team = make_team("QA Web")
    live = make_project(team, "Vivo")
    archived = make_project(team, "Archivado", is_active=False)
    assert list(Project.objects.active()) == [live]
    assert list(Project.objects.archived()) == [archived]