from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect,render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, UpdateView

from apps.accounts.models import User
from apps.teams.models import Membership, Role, Team

from .forms import *
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
class UserResetPasswordView(AdminRequiredMixin, View):
    """Generates a temporary password and shows it ONCE (it is never stored)."""

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Para cambiar tu propia contraseña usa el menú de tu perfil.")
            return redirect("panel:user_list")
        if not user.is_active:
            messages.error(request, "Activa al usuario antes de restablecer su contraseña.")
            return redirect("panel:user_list")

        temp_password = User.objects.reset_password(user)
        response = render(
            request,
            "panel/users/temp_password.html",
            {"target": user, "temp_password": temp_password},
        )
        response["Cache-Control"] = "no-store"
        return response


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
# --- Team members -----------------------------------------------------------
class TeamDetailView(AdminRequiredMixin, DetailView):
    """Team page: roster + form to add a person (this view also handles that POST)."""

    model = Team
    template_name = "panel/teams/detail.html"
    context_object_name = "team"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("add_form", MembershipAddForm(team=self.object))
        context["memberships"] = Membership.objects.roster(self.object)
        context["roles"] = Role.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = MembershipAddForm(request.POST, team=self.object)
        if form.is_valid():
            membership = form.save()
            messages.success(
                request,
                f"{membership.user.get_full_name()} agregado a {self.object.name} "
                f"como {membership.role.label}.",
            )
            return redirect("panel:team_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(add_form=form))


class MembershipRoleView(AdminRequiredMixin, View):
    """Changes someone's role in THIS team only."""

    def post(self, request, pk, membership_pk):
        membership = get_object_or_404(
            Membership.objects.select_related("user", "role"), pk=membership_pk, team_id=pk
        )
        form = MembershipRoleForm(request.POST)
        if form.is_valid():
            role = form.cleaned_data["role"]
            Membership.objects.filter(pk=membership.pk).set_role(role)
            messages.success(
                request, f"{membership.user.get_full_name()} ahora es {role.label} en este equipo."
            )
        else:
            messages.error(request, "Cargo no válido.")
        return redirect("panel:team_detail", pk=pk)


class MembershipRemoveView(AdminRequiredMixin, View):
    """Removes someone from THIS team (their other teams are untouched)."""

    def post(self, request, pk, membership_pk):
        membership = get_object_or_404(
            Membership.objects.select_related("user", "team"), pk=membership_pk, team_id=pk
        )
        name, team_name = membership.user.get_full_name(), membership.team.name
        membership.delete()
        messages.success(request, f"{name} fue quitado de {team_name}.")
        return redirect("panel:team_detail", pk=pk)