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
        ("node_man", "0081_auto_20240307_1656"),
    ]

    operations = [
        migrations.CreateModel(
            name="GsePackageDesc",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("created_by", models.CharField(default="", max_length=32, verbose_name="创建者")),
                ("updated_time", models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")),
                ("updated_by", models.CharField(blank=True, default="", max_length=32, verbose_name="修改者")),
                ("project", models.CharField(db_index=True, max_length=32, unique=True, verbose_name="工程名")),
                ("description", models.TextField(verbose_name="安装包描述")),
                ("description_en", models.TextField(blank=True, null=True, verbose_name="英文插件描述")),
                (
                    "category",
                    models.CharField(
                        choices=[("official", "official"), ("external", "external"), ("scripts", "scripts")],
                        max_length=32,
                        verbose_name="所属范围",
                    ),
                ),
            ],
            options={
                "verbose_name": "Gse包描述（GsePackageDesc）",
                "verbose_name_plural": "Gse包描述（GsePackageDesc）",
            },
        ),
        migrations.CreateModel(
            name="GsePackages",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("created_by", models.CharField(default="", max_length=32, verbose_name="创建者")),
                ("updated_time", models.DateTimeField(auto_now=True, null=True, verbose_name="更新时间")),
                ("updated_by", models.CharField(blank=True, default="", max_length=32, verbose_name="修改者")),
                ("pkg_name", models.CharField(max_length=128, verbose_name="压缩包名")),
                ("version", models.CharField(max_length=128, verbose_name="版本号")),
                ("project", models.CharField(db_index=True, max_length=32, verbose_name="工程名")),
                ("pkg_size", models.IntegerField(verbose_name="包大小")),
                ("pkg_path", models.CharField(max_length=128, verbose_name="包路径")),
                ("md5", models.CharField(max_length=32, verbose_name="md5值")),
                ("location", models.CharField(max_length=512, verbose_name="安装包链接")),
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
                ("is_ready", models.BooleanField(default=True, verbose_name="插件是否可用")),
                ("version_log", models.TextField(blank=True, null=True, verbose_name="版本日志")),
                ("version_log_en", models.TextField(blank=True, null=True, verbose_name="英文版本日志")),
            ],
            options={
                "verbose_name": "Gse包（GsePackages）",
                "verbose_name_plural": "Gse包（GsePackages）",
            },
        ),
    ]
