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
# Generated by Django 2.2.8 on 2021-04-08 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0037_auto_20210406_1136"),
    ]

    operations = [
        migrations.AddField(
            model_name="subscriptiontask",
            name="is_ready",
            field=models.BooleanField(default=False, verbose_name="是否准备就绪"),
        ),
        migrations.AlterField(
            model_name="processstatus",
            name="version",
            field=models.CharField(
                blank=True, db_index=True, default="", max_length=45, null=True, verbose_name="进程版本"
            ),
        ),
    ]
