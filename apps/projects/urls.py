from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.ProjectListView.as_view(), name="list"),
    path("archived/", views.ArchivedProjectListView.as_view(), name="archived"),
    path("new/", views.ProjectCreateView.as_view(), name="create"),
    path("<int:pk>/", views.ProjectDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", views.ProjectUpdateView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.ProjectArchiveView.as_view(), name="archive"),
    path("<int:pk>/reactivate/", views.ProjectReactivateView.as_view(), name="reactivate"),
    path("<int:pk>/assign/", views.ProjectAssignView.as_view(), name="assign"),
    path(
        "<int:pk>/assignments/<int:assignment_pk>/remove/",
        views.ProjectUnassignView.as_view(),
        name="unassign",
    ),
]