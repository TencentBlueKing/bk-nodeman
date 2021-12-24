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
from itertools import product

from django.db import migrations

from apps.node_man import constants


def replenish_plugin_template(apps, schema_editor):
    PluginConfigTemplate = apps.get_model("node_man", "PluginConfigTemplate")
    plugin_templates = PluginConfigTemplate.objects.all()
    for os_type, cpu_arch, template in product(constants.OS_TUPLE, constants.CPU_TUPLE, plugin_templates):
        PluginConfigTemplate.objects.update_or_create(
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
