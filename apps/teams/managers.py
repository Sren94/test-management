from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


# --- Role -------------------------------------------------------------------
class RoleQuerySet(models.QuerySet):
    pass


class RoleManager(models.Manager.from_queryset(RoleQuerySet)):
    pass


# --- Team -------------------------------------------------------------------
class TeamQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def inactive(self):
        return self.filter(is_active=False)

    def search(self, term):
        """Case-insensitive search by team name."""
        if not term:
            return self
        return self.filter(name__icontains=term)

    def with_status(self, status):
        """status: 'active', 'inactive' or anything else (= all)."""
        if status == "active":
            return self.active()
        if status == "inactive":
            return self.inactive()
        return self

    def with_counts(self):
        """Adds leaders_count and testers_count (only active users) in one query."""
        # Imported here, not at the top: models.py imports this file, so a top-level
        # import of models.py would be circular.
        from .models import RoleName

        active_user = Q(memberships__user__is_active=True)
        return self.annotate(
            leaders_count=Count(
                "memberships",
                filter=active_user & Q(memberships__role__name=RoleName.LEADER),
            ),
            testers_count=Count(
                "memberships",
                filter=active_user & Q(memberships__role__name=RoleName.TESTER),
            ),
        )

    def deactivate(self):
        return self.update(is_active=False, updated_at=timezone.now())

    def activate(self):
        return self.update(is_active=True, updated_at=timezone.now())


class TeamManager(models.Manager.from_queryset(TeamQuerySet)):
    def name_exists(self, name, exclude_pk=None):
        """True if another team already uses this name (ignoring upper/lower case)."""
        return self.filter(name__iexact=name).exclude(pk=exclude_pk).exists()


# --- Membership -------------------------------------------------------------
class MembershipQuerySet(models.QuerySet):
    def active(self):
        """Only memberships whose user AND team are active."""
        return self.filter(user__is_active=True, team__is_active=True)

    def with_details(self):
        """Loads team and role in the same query (no extra query per row)."""
        return self.select_related("team", "role")

    def current(self):
        """What the header shows: active memberships, with details, by team name."""
        return self.active().with_details().order_by("team__name")

    def by_role(self):
        """Active memberships ordered by role, then team (for grouping by role)."""
        return self.active().with_details().order_by("role__name", "team__name")


class MembershipManager(models.Manager.from_queryset(MembershipQuerySet)):
    pass