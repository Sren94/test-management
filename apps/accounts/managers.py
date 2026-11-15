from django.contrib.auth.models import UserManager as DjangoUserManager
class UserManager(DjangoUserManager):
    """Creates users with all their data.

    Teams and roles are NOT handled here: they live in the `teams` app,
    and a service there links the new user to a team.
    """

    def create_user(self, username, email, first_name, last_name, password=None, **extra_fields):
        if not all([username, email, first_name, last_name]):
            raise ValueError("username, email, first_name and last_name are required.")
        extra_fields["is_staff"] = False
        extra_fields["is_superuser"] = False
        extra_fields.setdefault("must_change_password", True)
        # Regular users start with their username as password (they must change it).
        return self._create_user(
            username,
            email,
            password or username,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        if not password:
            raise ValueError("A superuser must have a password.")
        if not all([username, email, extra_fields.get("first_name"), extra_fields.get("last_name")]):
            raise ValueError("username, email, first_name and last_name are required.")
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        extra_fields["must_change_password"] = False
        return self._create_user(username, email, password, **extra_fields)

