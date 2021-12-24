# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from collections import defaultdict
from itertools import product
from typing import Dict, List

from django.db import migrations, transaction

from apps.node_man import constants


def replenish_plugin_template(apps, schema_editor):
    replenish_platform_map: Dict[str, List] = defaultdict(list)
    target_platform_map: Dict[str, List] = {
        constants.OsType.LINUX: [constants.CpuType.x86_64, constants.CpuType.aarch64],
        constants.OsType.WINDOWS: [constants.CpuType.x86_64],
        constants.OsType.AIX: [constants.CpuType.powerpc],
        constants.OsType.SOLARIS: [constants.CpuType.sparc],
    }
    default_platform_map: Dict[str, List] = {
        constants.OsType.LINUX: [constants.CpuType.x86_64],
    }

    PluginConfigTemplate = apps.get_model("node_man", "PluginConfigTemplate")
    plugin_templates: List[PluginConfigTemplate] = PluginConfigTemplate.objects.all()

    # 取差集
    for os, cpu_arches in target_platform_map.items():
        if os not in default_platform_map:
            replenish_platform_map[os] = cpu_arches
        else:
            cpu_arch_diff_set = list(set(cpu_arches).difference(set(default_platform_map[os])))
            replenish_platform_map[os] = cpu_arch_diff_set

    with transaction.atomic(savepoint=False):
        for os_type, cpu_arch_list in replenish_platform_map.items():
            for cpu_arch, template in product(cpu_arch_list, plugin_templates):
                PluginConfigTemplate.objects.create(
                    plugin_name=template.plugin_name,
                    plugin_version=template.plugin_version,
                    name=template.name,
                    version=template.version,
                    is_main=template.is_main,
                    format=template.format,
                    file_path=template.file_path,
                    content=template.content,
                    is_release_version=template.is_release_version,
                    creator=template.creator,
                    create_time=template.create_time,
                    source_app_code=template.source_app_code,
                    cpu_arch=cpu_arch.lower(),
                    os=os_type.lower(),
                )


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0057_auto_20220224_1235"),
    ]

    operations = [
        migrations.RunPython(replenish_plugin_template),
    ]
