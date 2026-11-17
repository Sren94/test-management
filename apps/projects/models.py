from django.conf import settings
from django.db import models

from .managers import ProjectAssignmentManager, ProjectManager


class Project(models.Model):
    name = models.CharField(max_length=200)
    # Text, and NOT unique: several projects can share a SISAP folio.
    sisap_folio = models.CharField(max_length=50)
    team = models.ForeignKey("teams.Team", on_delete=models.PROTECT, related_name="projects")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_projects",
    )
    # "Deleting" a project archives it: its data is never lost.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProjectManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.sisap_folio} - {self.name}"


class ProjectAssignment(models.Model):
    """A person assigned to a project. Closing it (removed_at) keeps the history."""

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="project_assignments"
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)  # null = still assigned

    objects = ProjectAssignmentManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user"],
                condition=models.Q(removed_at__isnull=True),
                name="unique_current_project_assignment",
            ),
        ]

    def __str__(self) -> str:
        state = "assigned" if self.removed_at is None else "removed"
        return f"{self.user} - {self.project} ({state})"