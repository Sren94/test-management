from django.contrib.auth.models import UserManager as DjangoUserManager
from django.db import models
from django.db.models import Q

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
    def assignable_to(self, team):
        """Active, non-admin users that are not yet in the team."""
        return self.active().filter(is_superuser=False).exclude(memberships__team=team)

    def with_memberships(self):
        """Loads memberships with team and role (no query per row)."""
        return self.prefetch_related("memberships__team", "memberships__role")

    def deactivate(self):
        return self.update(is_active=False)

    def activate(self):
        return self.update(is_active=True)


class UserManager(DjangoUserManager.from_queryset(UserQuerySet)):
    """Creates users with all their data.

    Teams and roles are NOT handled here: they live in the `teams` app
    (see MembershipManager.create_user_with_membership).
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