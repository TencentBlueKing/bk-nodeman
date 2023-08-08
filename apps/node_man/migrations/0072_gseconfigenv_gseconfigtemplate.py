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

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0071_update_ap_gse_version_to_v2"),
    ]

    operations = [
        migrations.CreateModel(
            name="GseConfigEnv",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("env_value", models.TextField(verbose_name="环境变量值")),
                ("agent_name", models.CharField(max_length=32, verbose_name="Agent名称")),
                ("version", models.CharField(max_length=128, verbose_name="版本号")),
                (
                    "cpu_arch",
                    models.CharField(
                        choices=[
                            ("x86", "x86"),
                            ("x86_64", "x86_64"),
                            ("powerpc", "powerpc"),
                            ("aarch64", "aarch64"),
                            ("sparc", "sparc"),
                        ],
                        db_index=True,
                        default="x86_64",
                        max_length=32,
                        verbose_name="CPU类型",
                    ),
                ),
                (
                    "os",
                    models.CharField(
                        choices=[("windows", "windows"), ("linux", "linux"), ("aix", "aix"), ("solaris", "solaris")],
                        db_index=True,
                        default="linux",
                        max_length=32,
                        verbose_name="系统类型",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="GseConfigTemplate",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=32, verbose_name="配置文件名称")),
                ("content", models.TextField(verbose_name="配置内容")),
                ("agent_name", models.CharField(max_length=32, verbose_name="Agent名称")),
                ("version", models.CharField(max_length=128, verbose_name="版本号")),
                (
                    "cpu_arch",
                    models.CharField(
                        choices=[
                            ("x86", "x86"),
                            ("x86_64", "x86_64"),
                            ("powerpc", "powerpc"),
                            ("aarch64", "aarch64"),
                            ("sparc", "sparc"),
                        ],
                        db_index=True,
                        default="x86_64",
                        max_length=32,
                        verbose_name="CPU类型",
                    ),
                ),
                (
                    "os",
                    models.CharField(
                        choices=[("windows", "windows"), ("linux", "linux"), ("aix", "aix"), ("solaris", "solaris")],
                        db_index=True,
                        default="linux",
                        max_length=32,
                        verbose_name="系统类型",
                    ),
                ),
            ],
        ),
    ]
