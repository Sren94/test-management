from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from .forms import PasswordChangeForm
from .models import User


class HomeView(LoginRequiredMixin, TemplateView):
    """Landing page after login. Requires an authenticated user."""

    template_name = "home.html"


class PasswordChangeView(auth_views.PasswordChangeView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        User.objects.filter(pk=self.request.user.pk).mark_password_changed()
        return response