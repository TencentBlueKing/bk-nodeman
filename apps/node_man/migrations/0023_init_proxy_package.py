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

from apps.node_man import constants


def init_proxy_package(apps, schema_editor):
    packages = [
        "gse_client-windows-x86.tgz",
        "gse_client-windows-x86_64.tgz",
        "gse_client-linux-x86.tgz",
        "gse_client-linux-x86_64.tgz",
    ]

    if settings.BKAPP_RUN_ENV != constants.BkappRunEnvType.CE.value:
        packages.append("gse_client-aix-powerpc.tgz")

    AccessPoint = apps.get_model("node_man", "AccessPoint")
    AccessPoint.objects.update(proxy_package=packages)


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0022_accesspoint_proxy_package"),
    ]

    operations = [
        migrations.RunPython(init_proxy_package),
    ]
