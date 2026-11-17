from django.contrib.auth.mixins import UserPassesTestMixin

from apps.teams.models import Team


class CanCreateProjectMixin(UserPassesTestMixin):
    """Only people who belong to at least one active team can create projects.

    Anonymous users go to the login; admins and people without a team get a 403.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and Team.objects.of_member(user).exists()