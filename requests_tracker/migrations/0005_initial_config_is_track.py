from django.db import migrations

from requests_tracker.models import Config


def add_config_data(apps, schema_editor):
    Config.objects.get_or_create(key="is_track", value=False)


class Migration(migrations.Migration):

    dependencies = [
        ('requests_tracker', '0004_auto_20200314_2120'),
    ]

    operations = [
        migrations.RunPython(add_config_data),
    ]