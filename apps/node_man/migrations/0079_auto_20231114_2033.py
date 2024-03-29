# Generated by Django 3.2.4 on 2023-11-14 12:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0078_merge_20231114_2032"),
    ]

    operations = [
        migrations.AlterField(
            model_name="host",
            name="data_ip",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=45, null=True, verbose_name="数据IP"
            ),
        ),
        migrations.AlterField(
            model_name="host",
            name="inner_ipv6",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=45, null=True, verbose_name="内网IPv6"
            ),
        ),
        migrations.AlterField(
            model_name="host",
            name="login_ip",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=45, null=True, verbose_name="登录IP"
            ),
        ),
        migrations.AlterField(
            model_name="host",
            name="outer_ip",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=15, null=True, verbose_name="外网IP"
            ),
        ),
        migrations.AlterField(
            model_name="host",
            name="outer_ipv6",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=45, null=True, verbose_name="外网IPv6"
            ),
        ),
        migrations.AlterIndexTogether(
            name="host",
            index_together={("updated_at", "bk_host_id")},
        ),
    ]
