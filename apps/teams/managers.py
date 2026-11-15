from django.db import models


# --- Role -------------------------------------------------------------------
class RoleQuerySet(models.QuerySet):
    pass


class RoleManager(models.Manager.from_queryset(RoleQuerySet)):
    pass


# --- Team -------------------------------------------------------------------
class TeamQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)


class TeamManager(models.Manager.from_queryset(TeamQuerySet)):
    pass


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