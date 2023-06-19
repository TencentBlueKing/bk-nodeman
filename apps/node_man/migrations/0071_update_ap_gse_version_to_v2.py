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
from typing import List

from django.db import migrations
from django.db.models import QuerySet

from apps.node_man.constants import GSE_V2_PORT_DEFAULT_VALUE
from env.constants import GseVersion


def update_access_point_gse_version(apps, schema_editor):
    # 全新部署更新gse_vserion
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    access_points: List[AccessPoint] = list(AccessPoint.objects.all())
    access_point: AccessPoint = access_points[0]
    # 判断是否为全新部署
    if len(access_points) == 1 and access_point.port_config == GSE_V2_PORT_DEFAULT_VALUE:
        access_point.gse_version = GseVersion.V2.value
        access_point.save()


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0070_auto_20230613_1055"),
    ]

    operations = [
        migrations.RunPython(update_access_point_gse_version),
    ]
