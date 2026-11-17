from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import HomeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("panel/", include("apps.panel.urls")),
    path("projects/", include("apps.projects.urls")),
    path("", HomeView.as_view(), name="home"),
]