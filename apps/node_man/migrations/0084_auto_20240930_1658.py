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
        ('node_man', '0083_subscription_operate_info'),
    ]

    operations = [
        migrations.AddField(
            model_name='host',
            name='bk_idc_area_id',
            field=models.IntegerField(db_index=True, null=True, verbose_name='区域ID'),
        ),
        migrations.AddField(
            model_name='host',
            name='idc_city_id',
            field=models.CharField(blank=True, db_index=True, default='', max_length=16, null=True, verbose_name='城市ID'),
        ),
    ]
