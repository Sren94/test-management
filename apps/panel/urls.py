from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    # Users
    path("users/", views.UserListView.as_view(), name="user_list"),
    path("users/new/", views.UserCreateView.as_view(), name="user_create"),
    path("users/<int:pk>/edit/", views.UserUpdateView.as_view(), name="user_edit"),
    path("users/<int:pk>/toggle/", views.UserToggleActiveView.as_view(), name="user_toggle"),
    # Teams
    path("teams/", views.TeamListView.as_view(), name="team_list"),
    path("teams/new/", views.TeamCreateView.as_view(), name="team_create"),
    path("teams/<int:pk>/edit/", views.TeamUpdateView.as_view(), name="team_edit"),
    path("teams/<int:pk>/toggle/", views.TeamToggleActiveView.as_view(), name="team_toggle"),
]