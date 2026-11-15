from django.db import migrations

ROLE_NAMES = ["leader", "tester"]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("teams", "Role")
    for name in ROLE_NAMES:
        Role.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("teams", "0001_initial")]

    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]