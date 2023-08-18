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
        ("node_man", "0072_gseconfigenv_gseconfigtemplate"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="gseconfigenv",
            options={"verbose_name": "安装包环境变量", "verbose_name_plural": "安装包环境变量"},
        ),
        migrations.AlterModelOptions(
            name="gseconfigtemplate",
            options={"verbose_name": "安装包模板表", "verbose_name_plural": "安装包模板表"},
        ),
        migrations.AlterField(
            model_name="gseconfigenv",
            name="env_value",
            field=models.JSONField(verbose_name="环境变量值"),
        ),
    ]
