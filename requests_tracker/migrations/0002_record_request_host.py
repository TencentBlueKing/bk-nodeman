# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('requests_tracker', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='record',
            name='request_host',
            field=models.CharField(default='', max_length=128),
            preserve_default=False,
        ),
    ]
