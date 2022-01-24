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
from prettytable import PrettyTable

from apps.backend.healthz.constants import CheckerStatus
from apps.backend.healthz.define import init_healthz_node_metric
from apps.backend.healthz.processor import get_backend_healthz


class Command(BaseCommand):
    help = "Backend自监控检查指标"

    def handle(self, *args, **options):
        print("加载 Backend指标配置中...")
        healthz_config = [c["metric_alias"] for c in init_healthz_node_metric()]
        print("指标收集完成")
        print(f"Backend指标配置为: {healthz_config}")
        print("*" * 50)
        print("收集指标中请稍等...")
        backend_healthz = get_backend_healthz()
        print("指标收集完成")
        print("*" * 50)
        print("检查结果如下:")
        result_table = format_check_result(backend_healthz)
        print(result_table)


class Color:
    """
    彩色文字
    """

    RED = "\033[31;1m{}\033[0m"
    GREEN = "\033[32;1m{}\033[0m"
    YELLOW = "\033[33;1m{}\033[0m"


def format_check_result(healthz_result):
    """
    表格形式输出指标结果
    """
    HEALTHZ_FIELD_TITLES = ["node_name", "description", "category", "server_ip", "metric_alias", "status", "reason"]
    metric_status_map = {
        CheckerStatus.CHECKER_OK: Color.GREEN.format("正常"),
        CheckerStatus.CHECKER_FAILED: Color.RED.format("异常"),
    }
    result_table = PrettyTable(HEALTHZ_FIELD_TITLES)
    for healthz in healthz_result:
        healthz_result = {}
        # 筛选要展出的数据
        for metric, check_result in healthz.items():
            if metric == "result":
                metric_status = metric_status_map.get(check_result["status"], Color.YELLOW.format("检查程序报错"))
                reason = check_result["message"]
                healthz_result.update({"reason": reason, "status": metric_status})
            if metric in HEALTHZ_FIELD_TITLES:
                healthz_result.update({metric: check_result})
        # 结果排序
        sorted_result = []
        for field_namd in HEALTHZ_FIELD_TITLES:
            sorted_result.append(healthz_result[field_namd])
        result_table.add_row(sorted_result)
    return result_table
