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
import os

from django.db import migrations

from env.constants import GseVersion


def get_or_default(data, key, default):
    """
    从字典中获取指定键的值，如果键不存在则返回默认值。
    :param data: 字典
    :param key: 键
    :param default: 默认值
    :return: 键对应的值或默认值
    """
    return data.get(key, default)


def set_config_value(config, os_type, key, default):
    """
    设置配置字典中指定操作系统类型和键的值。
    :param config: 配置字典
    :param os_type: 操作系统类型（如 "windows", "linux"）
    :param key: 键
    :param default: 默认值
    """
    value = get_or_default(config[os_type], key, default)
    config[os_type][key] = value
    return config


def add_agent_config(apps, schema_editor):
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    aps = AccessPoint.objects.filter(gse_version=GseVersion.V2.value).all()

    for ap in aps:
        agent_config = ap.agent_config

        # 获取或设置 Windows 系统的 pluginipc 值
        agent_config = set_config_value(agent_config, "windows", "pluginipc", 26000)

        # 获取或设置 Linux 系统的 pluginipc 值
        linux_pluginipc_default = os.path.join(agent_config["linux"]["setup_path"], "agent/lib/ipc.state.message")
        agent_config = set_config_value(agent_config, "linux", "pluginipc", linux_pluginipc_default)

        # 获取或设置 Windows 系统的 alarm_event_data_id 值
        agent_config = set_config_value(agent_config, "windows", "alarm_event_data_id", 1000)

        # 获取或设置 Linux 系统的 alarm_event_data_id 值
        agent_config = set_config_value(agent_config, "linux", "alarm_event_data_id", 1000)

        ap.agent_config = agent_config
        ap.save()


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0087_update_ap_regionid_cityid"),
    ]

    operations = [
        migrations.RunPython(add_agent_config),
    ]
