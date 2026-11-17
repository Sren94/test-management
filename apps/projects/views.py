from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, ListView

from .models import Project, ProjectAssignment


class ProjectListView(LoginRequiredMixin, ListView):
    """Active projects the user can see (every project of their teams)."""

    template_name = "projects/list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        user = self.request.user
        return (
            Project.objects.visible_to(user)
            .active()
            .search(self.request.GET.get("q", "").strip())
            .with_details()
            .with_assignee_count()
            .with_user_flags(user)
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.request.GET.get("q", "")
        return context


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