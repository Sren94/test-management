from django import forms

from apps.teams.models import Team

from .models import Project


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