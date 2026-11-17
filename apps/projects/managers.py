from django.db import models
from django.db.models import Exists, OuterRef


# --- Project ----------------------------------------------------------------
class ProjectQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def archived(self):
        return self.filter(is_active=False)

    def with_details(self):
        """Loads team and creator in the same query (no extra query per row)."""
        return self.select_related("team", "created_by")

    def visible_to(self, user):
        """Projects the user can SEE: every project of the teams they belong to.

        Admins see all. Projects of inactive teams are hidden from everyone else.
        """
        from apps.teams.models import Membership

        if user.is_superuser:
            return self
        in_team = Membership.objects.filter(team=OuterRef("team"), user=user)
        return self.filter(team__is_active=True).filter(Exists(in_team))

    def manageable_by(self, user):
        """Projects the user can EDIT, archive and assign people to.

        - Admin: all.
        - Leader: every project of the teams where they are leader (per team).
        - Anyone else: only the projects they are currently assigned to.
        """
        from apps.teams.models import Membership, RoleName

        from .models import ProjectAssignment

        if user.is_superuser:
            return self
        leads_the_team = Membership.objects.filter(
            team=OuterRef("team"), user=user, role__name=RoleName.LEADER
        )
        is_assigned = ProjectAssignment.objects.current().filter(
            project=OuterRef("pk"), user=user
        )
        return self.visible_to(user).filter(Exists(leads_the_team) | Exists(is_assigned))


class ProjectManager(models.Manager.from_queryset(ProjectQuerySet)):
    pass


# --- ProjectAssignment ------------------------------------------------------
class ProjectAssignmentQuerySet(models.QuerySet):
    def current(self):
        """Assignments that are still in force (not closed)."""
        return self.filter(removed_at__isnull=True)


class ProjectAssignmentManager(models.Manager.from_queryset(ProjectAssignmentQuerySet)):
    pass