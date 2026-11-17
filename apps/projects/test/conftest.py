from types import SimpleNamespace

import pytest

from apps.projects.models import Project, ProjectAssignment
from apps.teams.models import Membership


@pytest.fixture
def make_project(db):
    def _make(team, name="Proyecto", folio="SISAP-1", **kwargs):
        return Project.objects.create(team=team, name=name, sisap_folio=folio, **kwargs)

    return _make


@pytest.fixture
def assign_to_project(db):
    def _assign(project, user, **kwargs):
        return ProjectAssignment.objects.create(project=project, user=user, **kwargs)

    return _assign


@pytest.fixture
def scenario(
    make_user, make_team, make_project, assign_to_project, leader_role, tester_role
):
    """Two teams.

    Web: a leader, a tester assigned to the project, a tester NOT assigned.
    Mobile: one tester assigned to its project.
    `nobody` belongs to no team.
    """
    web, mobile = make_team("QA Web"), make_team("QA Movil")
    people = {
        name: make_user(name)
        for name in ("lead_web", "tester_in", "tester_out", "tester_mobile", "nobody")
    }
    Membership.objects.assign(user=people["lead_web"], team=web, role=leader_role)
    Membership.objects.assign(user=people["tester_in"], team=web, role=tester_role)
    Membership.objects.assign(user=people["tester_out"], team=web, role=tester_role)
    Membership.objects.assign(user=people["tester_mobile"], team=mobile, role=tester_role)

    p_web = make_project(web, "Proyecto Web", "W-1")
    p_mobile = make_project(mobile, "Proyecto Movil", "M-1")
    assign_to_project(p_web, people["tester_in"])
    assign_to_project(p_mobile, people["tester_mobile"])
    return SimpleNamespace(web=web, mobile=mobile, p_web=p_web, p_mobile=p_mobile, **people)