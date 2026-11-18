from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView

from apps.teams.models import Team

from .forms import ProjectAssignForm, ProjectCreateForm, ProjectUpdateForm
from .mixins import CanCreateProjectMixin
from .models import Project, ProjectAssignment


class ProjectListView(LoginRequiredMixin, ListView):
    """Active projects the user can see, optionally filtered by one of their teams."""

    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20
    archived = False  # the archived list reuses this view

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
        projects = Project.objects.visible_to(user)
        projects = projects.archived() if self.archived else projects.active()
        return (
            projects.for_team(self.get_selected_team())
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
        context["archived"] = self.archived
        return context


class HomeView(ProjectListView):
    """Landing page: the same list of projects, right under the header."""

    template_name = "home.html"


class ArchivedProjectListView(ProjectListView):
    """Archived projects the user can see: the whole team can see them."""

    template_name = "projects/archived.html"
    archived = True


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """A project the user can see. Anything else is a 404."""

    template_name = "projects/detail.html"
    context_object_name = "project"

    def get_queryset(self):
        user = self.request.user
        return Project.objects.visible_to(user).with_details().with_user_flags(user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        context["assignments"] = (
            ProjectAssignment.objects.current().filter(project=project).with_user()
        )
        context["history"] = (
            ProjectAssignment.objects.closed()
            .filter(project=project)
            .with_user()
            .order_by("-removed_at")
        )
        if project.can_manage:
            context["assign_form"] = ProjectAssignForm(project=project)
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


class ProjectStateView(LoginRequiredMixin, View):
    """Base for archive / reactivate. POST only.

    Not visible -> 404. Visible but view-only -> 403.
    """

    def get_project(self, pk):
        user = self.request.user
        project = get_object_or_404(
            Project.objects.visible_to(user).with_user_flags(user), pk=pk
        )
        if not project.can_manage:
            raise PermissionDenied
        return project


class ProjectArchiveView(ProjectStateView):
    def post(self, request, pk):
        project = self.get_project(pk)
        if Project.objects.filter(pk=project.pk).archive():
            messages.success(
                request,
                f"Proyecto {project.name} archivado. Lo encuentras en Proyectos archivados.",
            )
        return redirect("projects:list")


class ProjectReactivateView(ProjectStateView):
    def post(self, request, pk):
        project = self.get_project(pk)
        if Project.objects.filter(pk=project.pk).reactivate():
            messages.success(request, f"Proyecto {project.name} reactivado.")
        return redirect("projects:detail", pk=project.pk)
class ProjectAssignView(ProjectStateView):
    def post(self, request, pk):
        project = self.get_project(pk)
        form = ProjectAssignForm(request.POST, project=project)
        if form.is_valid():
            user = form.cleaned_data["user"]
            if ProjectAssignment.objects.assign(project=project, user=user):
                messages.success(request, f"{user.get_full_name()} fue asignado al proyecto.")
            else:
                messages.error(request, "No se pudo asignar a esa persona.")
        else:
            messages.error(
                request, "Elige a una persona del equipo que aún no esté asignada."
            )
        return redirect("projects:detail", pk=project.pk)


class ProjectUnassignView(ProjectStateView):
    """Closes an assignment (it stays in the history)."""

    def post(self, request, pk, assignment_pk):
        project = self.get_project(pk)
        assignment = get_object_or_404(
            ProjectAssignment.objects.current().select_related("user"),
            pk=assignment_pk,
            project=project,
        )
        ProjectAssignment.objects.filter(pk=assignment.pk).close()
        messages.success(
            request, f"{assignment.user.get_full_name()} fue quitado del proyecto."
        )
        return redirect("projects:detail", pk=project.pk)