from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import UserManager
class User(AbstractUser):
    """Custom user. Logs in with `username`. Has no role: roles live in Membership."""
    first_name = models.CharField(_("first name"), max_length=150)
    last_name = models.CharField(_("last name"), max_length=150)
    email = models.EmailField(_("email address"), unique=False)
    must_change_password = models.BooleanField(default=True)

    objects = UserManager()

    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    def save(self, *args, **kwargs):
        self.email = self.email.lower()  # avoids Ana@x.com vs ana@x.com duplicates
        self.is_staff = self.is_superuser  # admins can always enter Django's admin
        super().save(*args, **kwargs)

    @property
    def is_admin(self) -> bool:
        """The system admin is simply a Django superuser."""
        return self.is_superuser