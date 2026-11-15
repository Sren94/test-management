from django import forms

from apps.accounts.models import User


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