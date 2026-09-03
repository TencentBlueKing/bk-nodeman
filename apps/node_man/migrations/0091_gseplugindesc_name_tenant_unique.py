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
        ('node_man', '0090_alter_subscription_node_type'),
    ]

    operations = [
        # 插件名不再全局唯一，改为同一租户内唯一，以支持跨租户同名插件
        migrations.AlterField(
            model_name='gseplugindesc',
            name='name',
            field=models.CharField(db_index=True, max_length=32, verbose_name='插件名'),
        ),
        migrations.AlterUniqueTogether(
            name='gseplugindesc',
            unique_together={('name', 'tenant_id')},
        ),
    ]
