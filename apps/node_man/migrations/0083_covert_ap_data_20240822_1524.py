# Generated by Django 3.2.4 on 2023-10-29 05:36

from django.db import migrations, models

from apps.node_man.utils.endpoint import EndPointTransform


def covert_ap_data(apps, schema_editor):
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    aps = AccessPoint.objects.all()
    for ap in aps:
        # 转换 gse 地址，从一对一关系，转换为两个列表
        ap.btfileserver = EndPointTransform().transform(legacy_endpoints=ap.btfileserver)
        ap.dataserver = EndPointTransform().transform(legacy_endpoints=ap.dataserver)
        ap.taskserver = EndPointTransform().transform(legacy_endpoints=ap.taskserver)
        ap.save()


class Migration(migrations.Migration):
    dependencies = [
        ("node_man", "0082_host_dept_name"),
    ]

    operations = [
        migrations.RunPython(covert_ap_data),
    ]