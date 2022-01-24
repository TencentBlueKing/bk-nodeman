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

from django.core.management.base import BaseCommand

from apps.backend.management.commands.backend_healthz import format_check_result
from apps.node_man.handlers.healthz.saas_healthz import get_saas_healthz

HEALTHZ_FIELD_TITLES = [
    "node_name",
    "description",
    "category",
    "metric_alias",
]


class Command(BaseCommand):
    help = "SaaS周边自监控检查指标"

    def handle(self, *args, **options):
        print("收集指标中请稍等...")
        saas_healthz = get_saas_healthz()
        print("指标收集完成")
        print("*" * 50)
        print("检查结果如下:")
        result_table = format_check_result(saas_healthz)
        print(result_table)
