# Generated by Django 3.2.4 on 2022-01-18 08:19

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0054_merge_20210925_0031"),
    ]

    operations = [
        migrations.AddField(
            model_name="accesspoint",
            name="callback_url",
            field=models.CharField(blank=True, default="", max_length=128, null=True, verbose_name="节点管理内网回调地址"),
        ),
        migrations.AlterField(
            model_name="host",
            name="cpu_arch",
            field=models.CharField(
                choices=[
                    ("x86", "x86"),
                    ("x86_64", "x86_64"),
                    ("powerpc", "powerpc"),
                    ("aarch64", "aarch64"),
                    ("sparc", "sparc"),
                ],
                db_index=True,
                default="x86_64",
                max_length=16,
                verbose_name="操作系统",
            ),
        ),
        migrations.AlterField(
            model_name="host",
            name="os_type",
            field=models.CharField(
                choices=[("LINUX", "LINUX"), ("WINDOWS", "WINDOWS"), ("AIX", "AIX"), ("SOLARIS", "SOLARIS")],
                db_index=True,
                default="LINUX",
                max_length=16,
                verbose_name="操作系统",
            ),
        ),
        migrations.AlterField(
            model_name="subscription",
            name="node_type",
            field=models.CharField(
                choices=[
                    ("TOPO", "动态实例（拓扑）"),
                    ("INSTANCE", "静态实例"),
                    ("SERVICE_TEMPLATE", "服务模板"),
                    ("SET_TEMPLATE", "集群模板"),
                ],
                db_index=True,
                max_length=20,
                verbose_name="节点类型",
            ),
        ),
        migrations.AlterField(
            model_name="subscriptioninstancerecord",
            name="update_time",
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now, verbose_name="更新时间"),
        ),
    ]
