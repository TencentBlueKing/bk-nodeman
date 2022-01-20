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
# Generated by Django 2.2.8 on 2021-03-09 01:16

import django_mysql.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0028_auto_20210208_1752"),
    ]

    operations = [
        migrations.AddField(
            model_name="gseplugindesc",
            name="node_manage_control",
            field=django_mysql.models.JSONField(blank=True, default=dict, null=True, verbose_name="节点管理管控插件信息"),
        ),
        migrations.AlterField(
            model_name="job",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "等待执行"),
                    ("RUNNING", "正在执行"),
                    ("SUCCESS", "执行成功"),
                    ("FAILED", "执行失败"),
                    ("PART_FAILED", "部分失败"),
                    ("TERMINATED", "已终止"),
                    ("REMOVED", "已移除"),
                ],
                default="RUNNING",
                max_length=45,
                verbose_name="任务状态",
            ),
        ),
        migrations.AlterField(
            model_name="processstatus",
            name="status",
            field=models.CharField(
                choices=[
                    ("RUNNING", "RUNNING"),
                    ("UNKNOWN", "UNKNOWN"),
                    ("TERMINATED", "TERMINATED"),
                    ("NOT_INSTALLED", "NOT_INSTALLED"),
                    ("UNREGISTER", "UNREGISTER"),
                    ("REMOVED", "REMOVED"),
                ],
                db_index=True,
                default="UNKNOWN",
                max_length=45,
                verbose_name="进程状态",
            ),
        ),
    ]
