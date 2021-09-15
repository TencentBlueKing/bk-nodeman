# -*- coding: utf-8 -*-
from django.db import migrations

from apps.node_man import constants


def update_gse_port(apps, schema_editor):
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    port = {"data_prometheus_port": constants.GSE_PORT_DEFAULT_VALUE["data_prometheus_port"]}
    aps = AccessPoint.objects.all()
    for ap in aps:
        ports = dict(ap.port_config)
        if "data_prometheus_port" not in ports:
            ap.port_config = {**ports, **port}
            ap.save()


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0002__init_isp_and_ap_20200121"),
        ("node_man", "0026_accesspoint_outer_callback_url"),
    ]

    operations = [
        migrations.RunPython(update_gse_port),
    ]
