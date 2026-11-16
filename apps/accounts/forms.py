from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.core.exceptions import ValidationError


class PasswordChangeForm(DjangoPasswordChangeForm):
    def clean_new_password1(self):
        password = self.cleaned_data.get("new_password1")
        if password and self.user.check_password(password):
            raise ValidationError("La nueva contraseña debe ser distinta a la actual.")
        return password