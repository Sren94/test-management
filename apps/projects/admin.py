from django.contrib import admin

from .models import Project, ProjectAssignment


class ProjectAssignmentInline(admin.TabularInline):
    model = ProjectAssignment
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("sisap_folio", "name", "team", "is_active", "created_at")
    list_filter = ("is_active", "team")
    search_fields = ("name", "sisap_folio")
    readonly_fields = ("created_at", "updated_at")
    inlines = [ProjectAssignmentInline]