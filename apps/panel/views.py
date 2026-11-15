from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, ListView, UpdateView

from apps.accounts.models import User

from .forms import UserCreateForm, UserUpdateForm
from .mixins import AdminRequiredMixin


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