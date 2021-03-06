# Generated by Django 3.2.4 on 2022-02-17 07:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0055_auto_20220118_1619"),
    ]

    operations = [
        migrations.CreateModel(
            name="PluginResourcePolicy",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plugin_name", models.CharField(db_index=True, max_length=32, verbose_name="插件名")),
                ("cpu", models.IntegerField(default=10, verbose_name="CPU限额")),
                ("mem", models.IntegerField(default=10, verbose_name="内存限额")),
                ("bk_biz_id", models.IntegerField(db_index=True, verbose_name="业务ID")),
                ("bk_obj_id", models.CharField(db_index=True, max_length=32, verbose_name="CMDB对象ID")),
                ("bk_inst_id", models.IntegerField(db_index=True, verbose_name="CMDB实例ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_index=True, verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "插件资源设置",
                "verbose_name_plural": "插件资源设置",
                "unique_together": {("plugin_name", "bk_obj_id", "bk_inst_id")},
            },
        ),
    ]
