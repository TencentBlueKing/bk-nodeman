# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.conf import settings
from django.db import migrations


def init_gse_port_config(apps, schema_editor):
    # 设置接入点hostid_path
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    aps = AccessPoint.objects.all()
    for ap in aps:
        agent_config = ap.agent_config
        linux_host_id = agent_config.get("linux", {}).get("host_id")
        agent_config.get("linux", {})["hostid_path"] = linux_host_id if linux_host_id else "/var/lib/gse/host/hostid"
        windows_host_id = agent_config.get("windows", {}).get("host_id")
        agent_config.get("windows", {})["hostid_path"] = (
            windows_host_id if windows_host_id else "C:\\gse\\data\\host\\hostid"
        )
        ap.agent_config = agent_config
        ap.save()


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0018_auto_20201009_1819"),
    ]

    operations = [
        migrations.RunPython(init_gse_port_config),
    ]
