from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q
from django.utils.crypto import get_random_string

# No look-alike characters (0/O, 1/l/I) so a temporary password is easy to dictate.
TEMP_PASSWORD_CHARS = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
TEMP_PASSWORD_LENGTH = 10


class UserQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def admins(self):
        return self.filter(is_superuser=True)

    def search(self, term):
        """Case-insensitive search by username, name or email."""
        if not term:
            return self
        return self.filter(
            Q(username__icontains=term)
            | Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
        )

    def with_status(self, status):
        """status: 'active', 'inactive' or anything else (= all)."""
        if status == "active":
            return self.active()
        if status == "inactive":
            return self.inactive()
        return self

    def with_memberships(self):
        """Loads memberships with team and role (no query per row)."""
        return self.prefetch_related("memberships__team", "memberships__role")

    def assignable_to(self, team):
        """Active, non-admin users that are not yet in the team."""
        return self.active().filter(is_superuser=False).exclude(memberships__team=team)

    def deactivate(self):
        return self.update(is_active=False)

    def activate(self):
        return self.update(is_active=True)

    def mark_password_changed(self):
        """The user chose their own password: lifts the forced change."""
        return self.update(must_change_password=False)


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    """Creates users with all their data.

    Teams and roles are NOT handled here: they live in the `teams` app.
    """

    def create_user(self, username, email, first_name, last_name, password=None, **extra_fields):
        if not all([username, email, first_name, last_name]):
            raise ValueError("username, email, first_name and last_name are required.")
        extra_fields["is_staff"] = False
        extra_fields["is_superuser"] = False
        extra_fields.setdefault("must_change_password", True)
        # Regular users start with their username as password (they must change it).
        return self._create_user(
            username,
            email,
            password or username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if not password:
            raise ValueError("A superuser must have a password.")
        if not all([username, email, extra_fields.get("first_name"), extra_fields.get("last_name")]):
            raise ValueError("username, email, first_name and last_name are required.")
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["must_change_password"] = False
        return self._create_user(username, email, password, **extra_fields)

    def reset_password(self, user):
        """Sets a random temporary password, forces a change, and returns it.

        The password is only returned here: it is never stored in plain text.
        Changing the password hash also closes the user's open sessions.
        """
        temp_password = get_random_string(TEMP_PASSWORD_LENGTH, TEMP_PASSWORD_CHARS)
        self.filter(pk=user.pk).update(
            password=make_password(temp_password), must_change_password=True
        )
        return temp_password