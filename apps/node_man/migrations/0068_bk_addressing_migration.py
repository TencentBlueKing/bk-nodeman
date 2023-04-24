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
from django.db import migrations

from apps.node_man.constants import CmdbAddressingType


def bk_addressing_migration(apps, schema_editor):
    # 主机寻址方式旧值迁移
    # https://github.com/TencentBlueKing/bk-nodeman/issues/1517
    Host = apps.get_model("node_man", "Host")
    Host.objects.filter(bk_addressing="0").update(bk_addressing=CmdbAddressingType.STATIC.value)
    Host.objects.filter(bk_addressing="1").update(bk_addressing=CmdbAddressingType.DYNAMIC.value)


class Migration(migrations.Migration):

    dependencies = [
        ("node_man", "0067_auto_20230201_1621"),
    ]

    operations = [
        migrations.RunPython(bk_addressing_migration),
    ]
