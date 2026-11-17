import pytest
from django.urls import reverse
from django.utils import timezone

from apps.projects.models import Project, ProjectAssignment
from apps.teams.models import Membership, Team

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
# --- home -------------------------------------------------------------------
def test_home_lists_the_users_projects(login, scenario):
    response = login(scenario.tester_in).get(reverse("home"))
    assert response.status_code == 200
    assert listed(response) == ["Proyecto Web"]


def test_home_for_a_user_without_projects(login, scenario):
    response = login(scenario.nobody).get(reverse("home"))
    assert response.status_code == 200
    assert listed(response) == []
    assert "No hay proyectos para mostrar" in response.content.decode()


def test_home_requires_login(client):
    response = client.get(reverse("home"))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]
# --- create -----------------------------------------------------------------
CREATE_URL = "projects:create"


def new_data(team, **overrides):
    return {"name": "Nuevo Proyecto", "sisap_folio": "S-100", "team": team.pk, **overrides}


def test_create_requires_login(client):
    response = client.get(reverse(CREATE_URL))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_admin_and_people_without_team_cannot_create(login, scenario, sysadmin_client):
    assert sysadmin_client.get(reverse(CREATE_URL)).status_code == 403
    assert login(scenario.nobody).get(reverse(CREATE_URL)).status_code == 403


def test_a_user_whose_only_team_is_inactive_cannot_create(login, scenario):
    Team.objects.filter(pk=scenario.web.pk).deactivate()
    assert login(scenario.lead_web).get(reverse(CREATE_URL)).status_code == 403


def test_the_form_only_offers_the_users_own_teams(login, scenario):
    response = login(scenario.tester_in).get(reverse(CREATE_URL))
    offered = [team.name for team in response.context["form"].fields["team"].queryset]
    assert offered == ["QA Web"]


def test_a_tester_creates_a_project_and_is_assigned(login, scenario):
    response = login(scenario.tester_out).post(reverse(CREATE_URL), new_data(scenario.web))
    project = Project.objects.get(name="Nuevo Proyecto")
    assert response.status_code == 302
    assert response["Location"] == reverse("projects:detail", args=[project.pk])
    assert project.team == scenario.web
    assert project.created_by == scenario.tester_out
    assert ProjectAssignment.objects.current().filter(
        project=project, user=scenario.tester_out
    ).exists()


def test_a_leader_can_create_too(login, scenario):
    response = login(scenario.lead_web).post(reverse(CREATE_URL), new_data(scenario.web))
    assert response.status_code == 302
    assert Project.objects.filter(name="Nuevo Proyecto", team=scenario.web).exists()


def test_cannot_create_in_another_team(login, scenario):
    response = login(scenario.tester_in).post(reverse(CREATE_URL), new_data(scenario.mobile))
    assert response.status_code == 200
    assert not Project.objects.filter(name="Nuevo Proyecto").exists()


def test_name_is_cleaned_and_the_folio_can_repeat(login, scenario):
    response = login(scenario.lead_web).post(
        reverse(CREATE_URL), new_data(scenario.web, name="  Nuevo   Proyecto ", sisap_folio="W-1")
    )
    assert response.status_code == 302
    assert Project.objects.filter(name="Nuevo Proyecto").exists()
    assert Project.objects.filter(sisap_folio="W-1").count() == 2


def test_create_button_only_shows_for_people_who_can_create(login, scenario, sysadmin_client):
    assert "Nuevo proyecto" in login(scenario.tester_in).get(reverse("home")).content.decode()
    assert "Nuevo proyecto" not in login(scenario.nobody).get(reverse("home")).content.decode()
    assert "Nuevo proyecto" not in sysadmin_client.get(reverse("home")).content.decode()


# --- edit -------------------------------------------------------------------
def edit_url(project):
    return reverse("projects:edit", args=[project.pk])


def test_edit_requires_login(client, scenario):
    assert client.get(edit_url(scenario.p_web)).status_code == 302


def test_leader_assigned_tester_and_admin_can_edit(login, scenario, sysadmin_client):
    for client in (login(scenario.lead_web), login(scenario.tester_in), sysadmin_client):
        response = client.post(
            edit_url(scenario.p_web), {"name": "Renombrado", "sisap_folio": "W-2"}
        )
        assert response.status_code == 302
        scenario.p_web.refresh_from_db()
        assert (scenario.p_web.name, scenario.p_web.sisap_folio) == ("Renombrado", "W-2")


def test_an_unassigned_tester_gets_403_and_nothing_changes(login, scenario):
    client = login(scenario.tester_out)
    assert client.get(edit_url(scenario.p_web)).status_code == 403
    response = client.post(edit_url(scenario.p_web), {"name": "Hack", "sisap_folio": "X"})
    assert response.status_code == 403
    scenario.p_web.refresh_from_db()
    assert scenario.p_web.name == "Proyecto Web"


def test_people_outside_the_team_get_404(login, scenario):
    assert login(scenario.tester_mobile).get(edit_url(scenario.p_web)).status_code == 404
    assert login(scenario.nobody).get(edit_url(scenario.p_web)).status_code == 404


def test_edit_cannot_change_the_team(login, scenario):
    login(scenario.lead_web).post(
        edit_url(scenario.p_web),
        {"name": "Proyecto Web", "sisap_folio": "W-1", "team": scenario.mobile.pk},
    )
    scenario.p_web.refresh_from_db()
    assert scenario.p_web.team == scenario.web


def test_a_closed_assignment_removes_the_edit_permission(login, scenario):
    ProjectAssignment.objects.filter(project=scenario.p_web, user=scenario.tester_in).update(
        removed_at=timezone.now()
    )
    assert login(scenario.tester_in).get(edit_url(scenario.p_web)).status_code == 403


def test_edit_button_only_shows_for_people_who_can_manage(login, scenario):
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    assert "Editar" in login(scenario.tester_in).get(url).content.decode()
    assert "Editar" not in login(scenario.tester_out).get(url).content.decode()
# --- team filter ------------------------------------------------------------
def two_team_tester(scenario, tester_role):
    Membership.objects.assign(user=scenario.tester_in, team=scenario.mobile, role=tester_role)
    return scenario.tester_in


def test_filter_chips_list_only_the_users_teams(login, scenario, tester_role):
    user = two_team_tester(scenario, tester_role)
    response = login(user).get(reverse("home"))
    assert [t.name for t in response.context["filter_teams"]] == ["QA Movil", "QA Web"]
    assert "Filtrar por equipo" in response.content.decode()


def test_filter_chips_are_hidden_with_a_single_team(login, scenario):
    response = login(scenario.tester_in).get(reverse("home"))
    assert "Filtrar por equipo" not in response.content.decode()


def test_filtering_by_team_shows_only_its_projects(login, scenario, tester_role):
    client = login(two_team_tester(scenario, tester_role))
    assert listed(client.get(reverse("home"))) == ["Proyecto Movil", "Proyecto Web"]
    response = client.get(reverse("home"), {"team": scenario.mobile.pk})
    assert listed(response) == ["Proyecto Movil"]
    assert response.context["selected_team"] == scenario.mobile


def test_filter_ignores_a_team_the_user_does_not_belong_to(login, scenario):
    response = login(scenario.tester_in).get(reverse("home"), {"team": scenario.mobile.pk})
    assert response.context["selected_team"] is None
    assert listed(response) == ["Proyecto Web"]


def test_filter_ignores_garbage_values(login, scenario):
    response = login(scenario.tester_in).get(reverse("home"), {"team": "abc"})
    assert response.status_code == 200
    assert listed(response) == ["Proyecto Web"]


def test_admin_can_filter_by_any_team(sysadmin_client, scenario):
    response = sysadmin_client.get(reverse("home"), {"team": scenario.mobile.pk})
    assert listed(response) == ["Proyecto Movil"]
    
# --- archive / reactivate ---------------------------------------------------
ARCHIVED = "projects:archived"


def archive_url(project):
    return reverse("projects:archive", args=[project.pk])


def reactivate_url(project):
    return reverse("projects:reactivate", args=[project.pk])


def test_leader_assigned_tester_and_admin_can_archive(login, scenario, sysadmin_client):
    for client in (login(scenario.lead_web), login(scenario.tester_in), sysadmin_client):
        response = client.post(archive_url(scenario.p_web))
        assert response.status_code == 302
        assert response["Location"] == reverse("projects:list")
        scenario.p_web.refresh_from_db()
        assert scenario.p_web.is_active is False
        Project.objects.filter(pk=scenario.p_web.pk).reactivate()


def test_leader_assigned_tester_and_admin_can_reactivate(login, scenario, sysadmin_client):
    for client in (login(scenario.lead_web), login(scenario.tester_in), sysadmin_client):
        Project.objects.filter(pk=scenario.p_web.pk).archive()
        response = client.post(reactivate_url(scenario.p_web))
        assert response.status_code == 302
        assert response["Location"] == reverse("projects:detail", args=[scenario.p_web.pk])
        scenario.p_web.refresh_from_db()
        assert scenario.p_web.is_active is True


def test_view_only_users_get_403_and_nothing_changes(login, scenario):
    client = login(scenario.tester_out)
    assert client.post(archive_url(scenario.p_web)).status_code == 403
    scenario.p_web.refresh_from_db()
    assert scenario.p_web.is_active is True
    Project.objects.filter(pk=scenario.p_web.pk).archive()
    assert client.post(reactivate_url(scenario.p_web)).status_code == 403
    scenario.p_web.refresh_from_db()
    assert scenario.p_web.is_active is False


def test_people_who_cannot_see_the_project_get_404(login, scenario):
    for user in (scenario.tester_mobile, scenario.nobody):
        client = login(user)
        assert client.post(archive_url(scenario.p_web)).status_code == 404
        assert client.post(reactivate_url(scenario.p_web)).status_code == 404


def test_leader_of_another_team_cannot_archive(login, scenario, leader_role):
    Membership.objects.filter(user=scenario.tester_mobile, team=scenario.mobile).update(
        role=leader_role
    )
    assert login(scenario.tester_mobile).post(archive_url(scenario.p_web)).status_code == 404


def test_a_closed_assignment_removes_the_archive_permission(login, scenario):
    ProjectAssignment.objects.filter(project=scenario.p_web, user=scenario.tester_in).update(
        removed_at=timezone.now()
    )
    assert login(scenario.tester_in).post(archive_url(scenario.p_web)).status_code == 403


def test_archive_needs_login_and_post(client, login, scenario):
    assert client.post(archive_url(scenario.p_web)).status_code == 302
    assert "/accounts/login/" in client.post(archive_url(scenario.p_web))["Location"]
    assert login(scenario.lead_web).get(archive_url(scenario.p_web)).status_code == 405
    assert login(scenario.lead_web).get(reactivate_url(scenario.p_web)).status_code == 405


def test_archiving_hides_the_project_but_keeps_its_assignments(login, scenario):
    client = login(scenario.lead_web)
    client.post(archive_url(scenario.p_web))
    assert listed(client.get(reverse("home"))) == []
    assert listed(client.get(reverse("projects:list"))) == []
    assert ProjectAssignment.objects.current().filter(
        project=scenario.p_web, user=scenario.tester_in
    ).exists()


def test_reactivating_brings_the_project_back_with_its_assignments(login, scenario):
    client = login(scenario.lead_web)
    client.post(archive_url(scenario.p_web))
    client.post(reactivate_url(scenario.p_web))
    assert listed(client.get(reverse("home"))) == ["Proyecto Web"]
    assert ProjectAssignment.objects.current().filter(project=scenario.p_web).count() == 1


def test_the_whole_team_sees_the_archived_projects(login, scenario):
    Project.objects.filter(pk=scenario.p_web.pk).archive()
    for user in (scenario.lead_web, scenario.tester_in, scenario.tester_out):
        assert listed(login(user).get(reverse(ARCHIVED))) == ["Proyecto Web"]
    assert listed(login(scenario.tester_mobile).get(reverse(ARCHIVED))) == []
    assert listed(login(scenario.nobody).get(reverse(ARCHIVED))) == []


def test_the_archived_list_has_no_active_projects(login, scenario):
    assert listed(login(scenario.lead_web).get(reverse(ARCHIVED))) == []


def test_admin_sees_every_archived_project(sysadmin_client, scenario):
    Project.objects.all().archive()
    assert listed(sysadmin_client.get(reverse(ARCHIVED))) == ["Proyecto Movil", "Proyecto Web"]


def test_archived_list_requires_login(client):
    response = client.get(reverse(ARCHIVED))
    assert response.status_code == 302
    assert "/accounts/login/" in response["Location"]


def test_archived_list_can_be_filtered_by_team(login, scenario, tester_role):
    Membership.objects.assign(user=scenario.tester_in, team=scenario.mobile, role=tester_role)
    Project.objects.all().archive()
    client = login(scenario.tester_in)
    assert listed(client.get(reverse(ARCHIVED))) == ["Proyecto Movil", "Proyecto Web"]
    response = client.get(reverse(ARCHIVED), {"team": scenario.mobile.pk})
    assert listed(response) == ["Proyecto Movil"]


def test_reactivate_button_only_shows_for_people_who_can_manage(login, scenario):
    Project.objects.filter(pk=scenario.p_web.pk).archive()
    assert "Reactivar</button>" in login(scenario.tester_in).get(reverse(ARCHIVED)).content.decode()
    assert "Reactivar</button>" not in login(scenario.tester_out).get(reverse(ARCHIVED)).content.decode()


def test_detail_shows_archive_or_reactivate_depending_on_the_state(login, scenario):
    client = login(scenario.lead_web)
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    page = client.get(url).content.decode()
    assert "Archivar</button>" in page
    assert "Reactivar</button>" not in page
    Project.objects.filter(pk=scenario.p_web.pk).archive()
    page = client.get(url).content.decode()
    assert "Reactivar</button>" in page
    assert "Archivar</button>" not in page


def test_view_only_users_do_not_see_the_archive_button(login, scenario):
    url = reverse("projects:detail", args=[scenario.p_web.pk])
    assert "Archivar</button>" not in login(scenario.tester_out).get(url).content.decode()


def test_the_header_menu_links_to_the_archived_projects(login, scenario, sysadmin_client):
    for client in (login(scenario.tester_out), login(scenario.nobody), sysadmin_client):
        assert "Proyectos archivados" in client.get(reverse("home")).content.decode()