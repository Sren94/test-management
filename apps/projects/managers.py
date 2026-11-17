from django.db import models, transaction
from django.db.models import BooleanField, Count, ExpressionWrapper, Exists, OuterRef, Q, Value
from django.utils import timezone
# --- Project ----------------------------------------------------------------
class ProjectQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def archived(self):
        return self.filter(is_active=False)

    def search(self, term):
        """Case-insensitive search by name or SISAP folio."""
        if not term:
            return self
        return self.filter(Q(name__icontains=term) | Q(sisap_folio__icontains=term))
    def for_team(self, team):
        """Only the projects of one team (None = no filter)."""
        if team is None:
            return self
        return self.filter(team=team)

    def with_details(self):
        """Loads team and creator in the same query (no extra query per row)."""
        return self.select_related("team", "created_by")

    def with_assignee_count(self):
        """Adds assignees_count: people currently assigned."""
        return self.annotate(
            assignees_count=Count("assignments", filter=Q(assignments__removed_at__isnull=True))
        )

    def with_user_flags(self, user):
        """Adds is_assigned and can_manage for this user, in the same query."""
        from apps.teams.models import Membership, RoleName

        from .models import ProjectAssignment

        is_assigned = Exists(
            ProjectAssignment.objects.current().filter(project=OuterRef("pk"), user=user)
        )
        if user.is_superuser:
            can_manage = Value(True, output_field=BooleanField())
        else:
            leads_the_team = Exists(
                Membership.objects.filter(
                    team=OuterRef("team"), user=user, role__name=RoleName.LEADER
                )
            )
            can_manage = ExpressionWrapper(
                leads_the_team | is_assigned, output_field=BooleanField()
            )
        return self.annotate(is_assigned=is_assigned, can_manage=can_manage)

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
    def archive(self):
        """Archives the active projects of this queryset. Returns how many changed."""
        return self.filter(is_active=True).update(is_active=False, updated_at=timezone.now())

    def reactivate(self):
        """Reactivates the archived projects of this queryset. Returns how many changed."""
        return self.filter(is_active=False).update(is_active=True, updated_at=timezone.now())



# --- ProjectAssignment ------------------------------------------------------
class ProjectAssignmentQuerySet(models.QuerySet):
    def current(self):
        """Assignments that are still in force (not closed)."""
        return self.filter(removed_at__isnull=True)

    def with_user(self):
        """Loads the user and orders by name."""
        return self.select_related("user").order_by("user__first_name", "user__last_name")


class ProjectAssignmentManager(models.Manager.from_queryset(ProjectAssignmentQuerySet)):
    pass
class ProjectManager(models.Manager.from_queryset(ProjectQuerySet)):
    @transaction.atomic
    def create_with_creator(self, *, name, sisap_folio, team, created_by):
        """Creates the project and assigns its creator, in one transaction."""
        from .models import ProjectAssignment

        project = self.create(
            name=name, sisap_folio=sisap_folio, team=team, created_by=created_by
        )
        ProjectAssignment.objects.create(project=project, user=created_by)
        return project