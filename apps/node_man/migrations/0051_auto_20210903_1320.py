# Generated by Django 2.2.6 on 2021-09-03 05:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0050_merge_20210812_2253"),
    ]

    operations = [
        migrations.AlterField(
            model_name="accesspoint",
            name="city_id",
            field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="城市id"),
        ),
        migrations.AlterField(
            model_name="accesspoint",
            name="region_id",
            field=models.CharField(blank=True, default="", max_length=255, null=True, verbose_name="区域id"),
        ),
    ]
