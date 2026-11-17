import pytest
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Project, ProjectAssignment

pytestmark = pytest.mark.django_db


def listed(response):
    return sorted(p.name for p in response.context["projects"])


# --- list -------------------------------------------------------------------
def test_list_requires_login(client):
    response = client.get(reverse("projects:list"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_list_shows_the_projects_of_the_users_teams(login, scenario):
    for user in (scenario.lead_web, scenario.tester_in, scenario.tester_out):
        assert listed(login(user).get(reverse("projects:list"))) == ["Proyecto Web"]
    assert listed(login(scenario.tester_mobile).get(reverse("projects:list"))) == ["Proyecto Movil"]
    assert listed(login(scenario.nobody).get(reverse("projects:list"))) == []


def test_admin_sees_every_project(sysadmin_client, scenario):
    response = sysadmin_client.get(reverse("projects:list"))
    assert listed(response) == ["Proyecto Movil", "Proyecto Web"]


def test_list_hides_archived_projects(login, scenario):
    Project.objects.filter(pk=scenario.p_web.pk).update(is_active=False)
    assert listed(login(scenario.lead_web).get(reverse("projects:list"))) == []


def test_list_search_by_folio(login, scenario, make_project):
    make_project(scenario.web, "Otro Proyecto", "ZZ-9")
    response = login(scenario.lead_web).get(reverse("projects:list"), {"q": "ZZ-9"})
    assert listed(response) == ["Otro Proyecto"]


def test_list_marks_what_each_user_can_manage(login, scenario):
    response = login(scenario.tester_out).get(reverse("projects:list"))
    project = response.context["projects"][0]
    assert (project.is_assigned, project.can_manage) == (False, False)
    response = login(scenario.tester_in).get(reverse("projects:list"))
    project = response.context["projects"][0]
    assert (project.is_assigned, project.can_manage) == (True, True)


# --- detail -----------------------------------------------------------------
def test_detail_opens_for_the_teams_members_and_admin(login, scenario, sysadmin_client):
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    for user in (scenario.lead_web, scenario.tester_in, scenario.tester_out):
        assert login(user).get(url).status_code == 200
    assert sysadmin_client.get(url).status_code == 200


def test_detail_is_404_for_people_outside_the_team(login, scenario):
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    assert login(scenario.tester_mobile).get(url).status_code == 404
    assert login(scenario.nobody).get(url).status_code == 404


def test_detail_requires_login(client, scenario):
    response = client.get(reverse("projects:detail", args=[scenario.p_web.pk]))
    assert response.status_code == 302


def test_detail_of_an_archived_project_still_opens(login, scenario):
    Project.objects.filter(pk=scenario.p_web.pk).update(is_active=False)
    response = login(scenario.lead_web).get(reverse("projects:detail", args=[scenario.p_web.pk]))
    assert response.status_code == 200
    assert "Archivado" in response.content.decode()


def test_detail_tells_who_can_only_view(login, scenario):
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    only_view = login(scenario.tester_out).get(url)
    assert only_view.context["project"].can_manage is False
    assert "Solo puedes ver este proyecto" in only_view.content.decode()
    can_manage = login(scenario.tester_in).get(url)
    assert can_manage.context["project"].can_manage is True
    assert "Tienes permiso" in can_manage.content.decode()


def test_detail_lists_only_current_assignments(login, scenario, assign_to_project):
    assign_to_project(scenario.p_web, scenario.tester_out)
    ProjectAssignment.objects.filter(project=scenario.p_web, user=scenario.tester_out).update(
        removed_at=timezone.now()
    )
    response = login(scenario.lead_web).get(reverse("projects:detail", args=[scenario.p_web.pk]))
    assert [a.user.username for a in response.context["assignments"]] == ["tester_in"]