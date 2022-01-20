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

from apps.node_man.constants import GSE_PORT_DEFAULT_VALUE


def init_gse_port_config(apps, schema_editor):
    # 设置接入点端口信息
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    AccessPoint.objects.update(port_config=GSE_PORT_DEFAULT_VALUE)


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0015_accesspoint_port_config"),
    ]

    operations = [
        migrations.RunPython(init_gse_port_config),
    ]
