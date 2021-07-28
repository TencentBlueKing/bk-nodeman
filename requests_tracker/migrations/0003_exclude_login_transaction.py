from django.db import migrations

from requests_tracker.models import Exclude


def add_exclude_data(apps, schema_editor):
    Exclude.objects.get_or_create(
        name='is_login_pattern', column=102, rule="*/is_login/*",
        is_active=1, category=1)
    Exclude.objects.get_or_create(
        name='get_user_pattern', column=102, rule="*/get_user/*",
        is_active=1, category=1)


class Migration(migrations.Migration):

    dependencies = [
        ('requests_tracker', '0002_record_request_host'),
    ]

    operations = [
        migrations.RunPython(add_exclude_data),
    ]