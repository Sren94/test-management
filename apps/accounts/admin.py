from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.utils.translation import gettext_lazy as _
from .models import User


class UserCreationForm(AdminUserCreationForm):
    class Meta(AdminUserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "last_name", "email")


class UserEditForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserEditForm
    list_display = ("username", "first_name", "last_name", "email", "is_superuser", "is_active")
    list_filter = ("is_superuser", "is_active")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (_("Access"), {"fields": ("must_change_password",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (None, {"classes": ("wide",), "fields": ("first_name", "last_name", "email")}),
    )