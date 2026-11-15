from django import forms

from apps.accounts.models import User
from apps.teams.models import Team


class UserCreateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email")
        labels = {
            "username": "Usuario",
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo",
        }

    def clean_email(self):
        return self.cleaned_data["email"].lower()

    def save(self, commit=True):
        """Creates the user through the manager (initial password = username)."""
        data = self.cleaned_data
        return User.objects.create_user(
            username=data["username"],
            email=data["email"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        labels = {
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo",
        }

    def clean_email(self):
        return self.cleaned_data["email"].lower()


class TeamForm(forms.ModelForm):
    """Create and edit a team. Members and roles are handled separately."""

    class Meta:
        model = Team
        fields = ("name",)
        labels = {"name": "Nombre del equipo"}

    def clean_name(self):
        name = " ".join(self.cleaned_data["name"].split())  # trims and collapses spaces
        if Team.objects.name_exists(name, exclude_pk=self.instance.pk):
            raise forms.ValidationError("Ya existe un equipo con ese nombre.")
        return name