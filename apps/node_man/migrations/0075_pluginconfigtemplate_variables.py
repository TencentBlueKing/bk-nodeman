# Generated by Django 3.2.4 on 2023-08-23 09:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('node_man', '0074_merge_20230818_1214'),
    ]

    operations = [
        migrations.AddField(
            model_name='pluginconfigtemplate',
            name='variables',
            field=models.JSONField(blank=True, default=None, null=True, verbose_name='配置变量'),
        ),
    ]