from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from .forms import PasswordChangeForm
from .models import User


class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        User.objects.filter(pk=self.request.user.pk).mark_password_changed()
        return response