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

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0048_merge_20210722_1733"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="job_type",
            field=models.CharField(
                choices=[
                    ("INSTALL_AGENT", "INSTALL_AGENT"),
                    ("RESTART_AGENT", "RESTART_AGENT"),
                    ("REINSTALL_AGENT", "REINSTALL_AGENT"),
                    ("UNINSTALL_AGENT", "UNINSTALL_AGENT"),
                    ("REMOVE_AGENT", "REMOVE_AGENT"),
                    ("UPGRADE_AGENT", "UPGRADE_AGENT"),
                    ("IMPORT_AGENT", "IMPORT_AGENT"),
                    ("RESTART_AGENT", "RESTART_AGENT"),
                    ("RELOAD_AGENT", "RELOAD_AGENT"),
                    ("MAIN_START_PLUGIN", "MAIN_START_PLUGIN"),
                    ("MAIN_STOP_PLUGIN", "MAIN_STOP_PLUGIN"),
                    ("MAIN_RESTART_PLUGIN", "MAIN_RESTART_PLUGIN"),
                    ("MAIN_RELOAD_PLUGIN", "MAIN_RELOAD_PLUGIN"),
                    ("MAIN_DELEGATE_PLUGIN", "MAIN_DELEGATE_PLUGIN"),
                    ("MAIN_UNDELEGATE_PLUGIN", "MAIN_UNDELEGATE_PLUGIN"),
                    ("MAIN_INSTALL_PLUGIN", "MAIN_INSTALL_PLUGIN"),
                    ("MAIN_STOP_AND_DELETE_PLUGIN", "MAIN_STOP_AND_DELETE_PLUGIN"),
                    ("DEBUG_PLUGIN", "DEBUG_PLUGIN"),
                    ("STOP_DEBUG_PLUGIN", "STOP_DEBUG_PLUGIN"),
                    ("PUSH_CONFIG_PLUGIN", "PUSH_CONFIG_PLUGIN"),
                    ("REMOVE_CONFIG_PLUGIN", "REMOVE_CONFIG_PLUGIN"),
                    ("PACKING_PLUGIN", "PACKING_PLUGIN"),
                    ("INSTALL_PROXY", "INSTALL_PROXY"),
                    ("RESTART_PROXY", "RESTART_PROXY"),
                    ("REINSTALL_PROXY", "REINSTALL_PROXY"),
                    ("REPLACE_PROXY", "REPLACE_PROXY"),
                    ("UNINSTALL_PROXY", "UNINSTALL_PROXY"),
                    ("UPGRADE_PROXY", "UPGRADE_PROXY"),
                    ("IMPORT_PROXY", "IMPORT_PROXY"),
                    ("RESTART_PROXY", "RESTART_PROXY"),
                    ("RELOAD_PROXY", "RELOAD_PROXY"),
                ],
                default="INSTALL_PROXY",
                max_length=45,
                verbose_name="作业类型",
            ),
        ),
    ]
