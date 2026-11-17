from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, FormView, ListView, UpdateView

from apps.teams.models import Team

from .forms import ProjectCreateForm, ProjectUpdateForm
from .mixins import CanCreateProjectMixin
from .models import Project, ProjectAssignment


class ProjectListView(LoginRequiredMixin, ListView):
    """Active projects the user can see, optionally filtered by one of their teams."""

    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_filter_teams(self):
        if not hasattr(self, "_filter_teams"):
            self._filter_teams = list(
                Team.objects.visible_to(self.request.user).order_by("name")
            )
        return self._filter_teams

    def get_selected_team(self):
        """The team chosen in the filter, only if the user can really see it."""
        raw = self.request.GET.get("team", "")
        for team in self.get_filter_teams():
            if str(team.pk) == raw:
                return team
        return None

    def get_queryset(self):
        user = self.request.user
        return (
            Project.objects.visible_to(user)
            .active()
            .for_team(self.get_selected_team())
            .search(self.request.GET.get("q", "").strip())
            .with_details()
            .with_assignee_count()
            .with_user_flags(user)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        context["filter_teams"] = self.get_filter_teams()
        context["selected_team"] = self.get_selected_team()
        context["can_create"] = Team.objects.of_member(self.request.user).exists()
        return context


class HomeView(ProjectListView):
    """Landing page: the same list of projects, right under the header."""

    template_name = "home.html"


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """A project the user can see. Anything else is a 404."""

    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_queryset(self):
        user = self.request.user
        return Project.objects.visible_to(user).with_details().with_user_flags(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["assignments"] = (
            ProjectAssignment.objects.current().filter(project=self.object).with_user()
        )
        return context
class ProjectCreateView(CanCreateProjectMixin, FormView):
    template_name = "projects/form.html"
    form_class = ProjectCreateForm
    extra_context = {
        "title": "Nuevo proyecto",
        "intro": "Quedarás asignado al proyecto automáticamente.",
        "submit_label": "Crear proyecto",
        "cancel_url": reverse_lazy("projects:list"),
    }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.project = form.save()
        messages.success(self.request, f"Proyecto {self.project.name} creado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:detail", args=[self.project.pk])


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """Visible but not manageable -> 403. Not visible at all -> 404."""

    form_class = ProjectUpdateForm
    template_name = "projects/form.html"
    extra_context = {"title": "Editar proyecto", "submit_label": "Guardar cambios"}

    def get_queryset(self):
        user = self.request.user
        return Project.objects.visible_to(user).with_user_flags(user)

    def get_object(self, queryset=None):
        project = super().get_object(queryset)
        if not project.can_manage:
            raise PermissionDenied
        return project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["cancel_url"] = self.get_success_url()
        return context

    def form_valid(self, form):
        messages.success(self.request, f"Proyecto {self.object.name} actualizado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("projects:detail", args=[self.object.pk])