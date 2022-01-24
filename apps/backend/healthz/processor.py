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


import json
import time
from importlib import import_module

from django.conf import settings
from django.template import Context, Template

from apps.backend.healthz import key
from apps.backend.healthz.checker import CheckerTask, HealthChecker
from apps.backend.healthz.conf import healthz_list
from apps.backend.healthz.define import init_healthz_node_metric
from apps.backend.utils.healthz import get_local_ip
from apps.node_man.handlers.healthz.saas_healthz import deep_parsing_metric_info
from common.log import logger

now = time.time()
checker = HealthChecker()
ip = get_local_ip()


def load_category(category):
    import_module("apps.backend.healthz.checker.%s_checker" % category)


def render_collect_args(config):
    collect_args = config["collect_args"]
    if not collect_args:
        return {}
    template = Template(collect_args)
    return json.loads(
        template.render(
            Context(
                {
                    "key": key,
                    "settings": settings,
                    "config": config,
                    "ip": ip,
                }
            )
        )
    )


def convert_config_to_task(config):
    try:
        return CheckerTask(
            config["collect_metric"],
            render_collect_args(config),
        )
    except Exception as err:
        print("create task[%s] failed: %s", config["collect_metric"], err)


def check_tasks(healthz_configs):
    check_result = []
    for config in healthz_configs:
        tasks = []
        if config["category"] in healthz_list or len(healthz_list) == 0:
            load_category(category=config["category"])
            task = convert_config_to_task(config)
            if task:
                tasks.append(task)
        results = checker.check_tasks(tasks)
        for result in results:
            check_result.append(
                {
                    "metric_alias": config["metric_alias"],
                    "result": result.as_json(),
                    "server_ip": ip,
                }
            )
    return check_result


class HealthzProcessor(object):
    """
    Healthz Processor
    """

    def process(self, healthz_configs):
        check_result = {}
        try:
            check_result = check_tasks(healthz_configs)
        except Exception as e:
            logger.exception("get exception: %s" % e)
        return check_result


def get_backend_healthz():
    """
    获取backend自监控指标
    """
    # 初始化指标
    healthz_metrics_configs = init_healthz_node_metric()
    # 获取指标
    backend_check_result = HealthzProcessor().process(healthz_metrics_configs)
    config_mappings = {c["metric_alias"]: c for c in healthz_metrics_configs}

    metric_infos = []
    for record in backend_check_result:
        metric_info = config_mappings.get(record["metric_alias"], {}).copy()
        metric_info.update(record)
        metric_info["solution"] = json.loads(metric_info.get("solution") or "[]")
        metric_info["result"] = json.loads(metric_info["result"])

        if isinstance(metric_info["result"]["value"], dict):
            metric_info["result"]["value"] = [metric_info["result"]["value"]]
        if isinstance(metric_info["result"]["value"], (list, tuple)):
            try:
                for sub_info in deep_parsing_metric_info(metric_info):
                    metric_infos.append(sub_info)
            except TypeError:
                metric_infos.append(metric_info)
        else:
            metric_infos.append(metric_info)
    return metric_infos
