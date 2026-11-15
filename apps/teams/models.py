from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from .managers import MembershipManager, RoleManager, TeamManager



class RoleName(models.TextChoices):
    """Names the code relies on. Use these constants, never loose strings."""

    LEADER = "leader", "Leader"
    TESTER = "tester", "Tester"

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)
    objects = RoleManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name
    @property
    def label(self) -> str:
        """Spanish label shown in the UI. The stored name stays in English."""
        labels = {RoleName.LEADER: "Líder", RoleName.TESTER: "Tester"}
        return labels.get(self.name, self.name.capitalize())


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Everyone in the team, whatever their role: team.members / user.teams
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="Membership", related_name="teams"
    )
    objects = TeamManager()

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    """One user in one team with one role. The role belongs to THIS team only.

    PROTECT on user and team: nothing with memberships can be deleted by accident.
    To remove someone or something, deactivate it (is_active = False).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="memberships"
    )
    team = models.ForeignKey(Team, on_delete=models.PROTECT, related_name="memberships")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="memberships")
    created_at = models.DateTimeField(auto_now_add=True)
    objects = MembershipManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "team"], name="unique_user_team_membership"),
        ]

    def __str__(self) -> str:
        return f"{self.user} - {self.team} ({self.role})"