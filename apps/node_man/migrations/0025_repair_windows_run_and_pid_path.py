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


def repair_run_path(apps, schema_editor):
    # 修复windows run and pid path
    AccessPoint = apps.get_model("node_man", "AccessPoint")
    ProcControl = apps.get_model("node_man", "ProcControl")
    aps = AccessPoint.objects.all()
    win_run_path = os.getenv("BKAPP_GSE_WIN_AGENT_RUN_DIR") or "C:\\gse\\logs"
    run_dir_suffix = ""
    for ap in aps:
        agent_config = ap.agent_config
        ap_run_path = agent_config.get("windows", {}).get("run_path")
        windows_run_path = ap_run_path or win_run_path
        agent_config.get("windows", {})["run_path"] = windows_run_path
        ap.agent_config = agent_config
        ap.save()
        run_dir_suffix = windows_run_path.split("\\")[-1]

    pcs = ProcControl.objects.filter(os="windows")
    for proc in pcs:
        proc.pid_path = proc.pid_path.replace("\\run\\", "\\{}\\".format(run_dir_suffix))
        proc.save()


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0024_accesspoint_bscp_config"),
    ]

    operations = [
        migrations.RunPython(repair_run_path),
    ]
