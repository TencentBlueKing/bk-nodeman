# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


def init_database(apps, schema_editor):
    cursor = schema_editor.connection.cursor()
    for table in ["Records", "Filters", "Excludes"]:
        try:
            cursor.execute('DROP TABLE "{0}"'.format(table))
        except Exception:
            pass


class Migration(migrations.Migration):
    dependencies = [('auth', '0006_require_contenttypes_0002'), ]

    operations = [
        migrations.RunPython(init_database),
        migrations.CreateModel(
            name='Exclude',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('is_active', models.BooleanField(default=False)),
                ('column', models.PositiveSmallIntegerField(
                    choices=[(0, b'api_uid'), (10, b'method'), (100, b'url:scheme'), (101, b'url:netloc'),
                             (102, b'url:path'), (103, b'url:query'), (104, b'url:fragment')])),
                ('category', models.PositiveSmallIntegerField(default=0, choices=[(0, b'equal'), (1, b'basic-re'),
                                                                                  (2, b'extended-re')])),
                ('rule', models.CharField(max_length=1024)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'Excludes',
            },
        ),
        migrations.CreateModel(
            name='Filter',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
                ('is_active', models.BooleanField(default=False)),
                ('column', models.PositiveSmallIntegerField(
                    choices=[(0, b'api_uid'), (10, b'method'), (100, b'url:scheme'), (101, b'url:netloc'),
                             (102, b'url:path'), (103, b'url:query'), (104, b'url:fragment')])),
                ('category', models.PositiveSmallIntegerField(default=0, choices=[(0, b'equal'), (1, b'basic-re'),
                                                                                  (2, b'extended-re')])),
                ('rule', models.CharField(max_length=1024)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('last_modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'Filters',
            },
        ),
        migrations.CreateModel(
            name='Record',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uid', models.UUIDField(unique=True)),
                ('api_uid', models.CharField(default=b'', max_length=64, blank=True)),
                ('state', models.CharField(default=b'CREATED', max_length=16,
                                           choices=[(b'FAILURE', b'FAILURE'), (b'IN_PROGRESS', b'IN_PROGRESS'),
                                                    (b'SUCCESS', b'SUCCESS'), (b'CREATED', b'CREATED')])),
                ('remark', models.CharField(default=b'', max_length=255, blank=True)),
                ('method', models.CharField(default=b'GET', max_length=8,
                                            choices=[(b'HEAD', b'HEAD'), (b'GET', b'GET'), (b'PATCH', b'PATCH'),
                                                     (b'PUT', b'PUT'), (b'POST', b'POST'), (b'OPTIONS', b'OPTIONS'),
                                                     (b'DELETE', b'DELETE')])),
                ('url', models.URLField(max_length=255)),
                ('request_message', models.TextField(blank=True)),
                ('operator', models.CharField(max_length=255)),
                ('status_code', models.PositiveSmallIntegerField(default=0)),
                ('response_message', models.TextField(blank=True)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now)),
                ('duration', models.DurationField(null=True, blank=True)),
            ],
            options={
                'db_table': 'Records',
            },
        ),
    ]
