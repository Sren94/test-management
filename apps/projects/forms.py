from django import forms

from apps.accounts.models import User
from apps.teams.models import Team

from .models import Project, ProjectAssignment

class ProjectCreateForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("name", "sisap_folio", "team")
        labels = {"name": "Nombre", "sisap_folio": "Folio SISAP", "team": "Equipo"}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        teams = Team.objects.of_member(user).order_by("name")
        self.fields["team"].queryset = teams  # only the user's own teams
        self.fields["team"].empty_label = "Selecciona un equipo"
        if teams.count() == 1:
            self.fields["team"].initial = teams.first()

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())

    def save(self, commit=True):
        """Creates the project through the manager (the creator is assigned)."""
        data = self.cleaned_data
        return Project.objects.create_with_creator(
            name=data["name"],
            sisap_folio=data["sisap_folio"],
            team=data["team"],
            created_by=self.user,
        )


class ProjectUpdateForm(forms.ModelForm):
    """The team is not editable: a project stays in the team that created it."""

    class Meta:
        model = Project
        fields = ("name", "sisap_folio")
        labels = {"name": "Nombre", "sisap_folio": "Folio SISAP"}

    def clean_name(self):
        return " ".join(self.cleaned_data["name"].split())
class ProjectAssignForm(forms.Form):
    """Picks a person of the project's team who is not assigned yet."""

    user = forms.ModelChoiceField(
        label="Persona",
        queryset=User.objects.none(),
        empty_label="Selecciona una persona",
    )

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = ProjectAssignment.objects.candidates(project)
        self.fields["user"].label_from_instance = lambda u: f"{u.get_full_name()} ({u.username})"