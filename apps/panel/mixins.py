from django.contrib.auth.mixins import UserPassesTestMixin


class AdminRequiredMixin(UserPassesTestMixin):
    """Only system admins (superusers) can use the panel.

    Anonymous users are sent to the login; logged-in non-admins get a 403.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.is_superuser