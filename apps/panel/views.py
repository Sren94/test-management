from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, UpdateView

from apps.accounts.models import User
from apps.teams.models import Team

from .forms import TeamForm, UserCreateForm, UserUpdateForm
from .mixins import AdminRequiredMixin


# --- Users ------------------------------------------------------------------
class UserListView(AdminRequiredMixin, ListView):
    template_name = "panel/users/list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        return (
            User.objects.search(self.request.GET.get("q", "").strip())
            .with_status(self.request.GET.get("status", "active"))
            .with_memberships()
            .order_by("first_name", "last_name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "active")
        return context


class UserCreateView(AdminRequiredMixin, FormView):
    template_name = "panel/users/form.html"
    form_class = UserCreateForm
    success_url = reverse_lazy("panel:user_list")
    extra_context = {
        "title": "Nuevo usuario",
        "intro": (
            "La contraseña inicial será el nombre de usuario y deberá cambiarla al entrar. "
            "El equipo y el cargo se asignan después, desde el panel de equipos."
        ),
        "submit_label": "Crear usuario",
    }

    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request, f"Usuario {user.username} creado. Su contraseña inicial es su usuario."
        )
        return super().form_valid(form)


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "panel/users/form.html"
    success_url = reverse_lazy("panel:user_list")
    extra_context = {"title": "Editar usuario", "submit_label": "Guardar cambios"}

    def form_valid(self, form):
        messages.success(self.request, f"Usuario {self.object.username} actualizado.")
        return super().form_valid(form)


class UserToggleActiveView(AdminRequiredMixin, View):
    """Deactivates or reactivates a user. Nothing is ever deleted."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
        elif user.is_active:
            User.objects.filter(pk=pk).deactivate()
            messages.success(request, f"Usuario {user.username} desactivado.")
        else:
            User.objects.filter(pk=pk).activate()
            messages.success(request, f"Usuario {user.username} activado.")
        return redirect("panel:user_list")


# --- Teams ------------------------------------------------------------------
class TeamListView(AdminRequiredMixin, ListView):
    template_name = "panel/teams/list.html"
    context_object_name = "teams"
    paginate_by = 20

    def get_queryset(self):
        return (
            Team.objects.search(self.request.GET.get("q", "").strip())
            .with_status(self.request.GET.get("status", "active"))
            .with_counts()
            .order_by("name")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["status"] = self.request.GET.get("status", "active")
        return context


class TeamCreateView(AdminRequiredMixin, CreateView):
    model = Team
    form_class = TeamForm
    template_name = "panel/teams/form.html"
    success_url = reverse_lazy("panel:team_list")
    extra_context = {
        "title": "Nuevo equipo",
        "intro": "El equipo se crea vacío. Las personas y sus cargos se asignan después.",
        "submit_label": "Crear equipo",
    }

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Equipo {self.object.name} creado.")
        return response


class TeamUpdateView(AdminRequiredMixin, UpdateView):
    model = Team
    form_class = TeamForm
    template_name = "panel/teams/form.html"
    success_url = reverse_lazy("panel:team_list")
    extra_context = {"title": "Editar equipo", "submit_label": "Guardar cambios"}

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Equipo {self.object.name} actualizado.")
        return response


class TeamToggleActiveView(AdminRequiredMixin, View):
    """Deactivates or reactivates a team. Its memberships are kept untouched."""

    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if team.is_active:
            Team.objects.filter(pk=pk).deactivate()
            messages.success(request, f"Equipo {team.name} desactivado.")
        else:
            Team.objects.filter(pk=pk).activate()
            messages.success(request, f"Equipo {team.name} activado.")
        return redirect("panel:team_list")