import pytest

from apps.accounts.models import User
from apps.teams.models import Membership

pytestmark = pytest.mark.django_db


def usernames(queryset):
    return sorted(user.username for user in queryset)


def test_search_matches_username_name_and_email(make_user):
    make_user("ana", first_name="Ana", last_name="Lopez")
    make_user("beto", first_name="Beto", last_name="Ruiz")
    assert usernames(User.objects.search("ana")) == ["ana"]
    assert usernames(User.objects.search("RUIZ")) == ["beto"]
    assert usernames(User.objects.search("beto@example")) == ["beto"]


def test_search_with_empty_term_returns_everyone(make_user):
    make_user("ana")
    make_user("beto")
    assert usernames(User.objects.search("")) == ["ana", "beto"]


def test_status_filters(make_user):
    make_user("on")
    make_user("off", is_active=False)
    assert usernames(User.objects.with_status("active")) == ["on"]
    assert usernames(User.objects.with_status("inactive")) == ["off"]
    assert usernames(User.objects.with_status("all")) == ["off", "on"]


def test_deactivate_and_activate(make_user):
    user = make_user("ana")
    User.objects.filter(pk=user.pk).deactivate()
    user.refresh_from_db()
    assert user.is_active is False
    User.objects.filter(pk=user.pk).activate()
    user.refresh_from_db()
    assert user.is_active is True


def test_assignable_to_excludes_members_admins_and_inactive(
    make_user, make_team, leader_role, sysadmin
):
    team = make_team("QA Web")
    member = make_user("member")
    free = make_user("free")
    make_user("inactive", is_active=False)
    Membership.objects.assign(user=member, team=team, role=leader_role)
    assert usernames(User.objects.assignable_to(team)) == [free.username]


def test_reset_password_returns_a_temporary_password(make_user):
    user = make_user("ana")
    temp = User.objects.reset_password(user)
    user.refresh_from_db()
    assert len(temp) == 10
    assert user.check_password(temp)
    assert not user.check_password("ana")
    assert user.must_change_password is True


def test_reset_password_gives_a_different_password_each_time(make_user):
    user = make_user("ana")
    assert User.objects.reset_password(user) != User.objects.reset_password(user)


def test_mark_password_changed(make_user):
    user = make_user("ana", must_change_password=True)
    User.objects.filter(pk=user.pk).mark_password_changed()
    user.refresh_from_db()
    assert user.must_change_password is False