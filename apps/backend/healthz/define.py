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


import copy
import json

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.healthz.constants import HEALTHZ_FIELD_NAMES
from config.default import CELERY_QUEUES

redis_metrics = [
    {
        "category": "redis",
        "collect_type": "backend",
        "description": _("Redis 状态"),
        "collect_metric": "redis.status",
        "solution": "",
        "node_name": "redis",
        "metric_alias": "redis.status",
        "collect_args": "{}",
    },
    {
        "category": "redis",
        "collect_type": "backend",
        "description": _("Redis 可读状态"),
        "collect_metric": "redis.read.status",
        "solution": "",
        "node_name": "redis",
        "metric_alias": "redis.read.status",
        "collect_args": "{}",
    },
    {
        "category": "redis",
        "collect_type": "backend",
        "description": _("Redis 可写状态"),
        "collect_metric": "redis.write.status",
        "solution": "",
        "node_name": "redis",
        "metric_alias": "redis.write.status",
        "collect_args": "{}",
    },
]

mysql_metrics = [
    {
        "category": "database",
        "collect_type": "backend",
        "description": _("数据库状态"),
        "collect_metric": "database.status",
        "solution": "",
        "node_name": "mysql",
        "metric_alias": "database.status",
        "collect_args": "{}",
    },
]

rabbitmq_metrics = [
    {
        "category": "rabbitmq",
        "collect_type": "backend",
        "description": _("rabbitmq 队列长度, 单个队列阀值为%s条" % settings.RABBITMQ_MAX_MESSAGE_COUNT),
        "collect_metric": "rabbitmq.status",
        "solution": "",
        "node_name": "rabbitmq",
        "metric_alias": "rabbitmq.status",
        "collect_args": "{}",
    }
]

celery_queues_names = {"queues": [queue.name for queue in CELERY_QUEUES]}
celery_metrics = [
    {
        "category": "celery",
        "collect_type": "backend",
        "description": _("celery beat 状态"),
        "node_name": "celery",
        "metric_alias": "celery.beat.status",
        "collect_metric": "celery.beat_process.status",
        "collect_args": '{"process_name": "nodeman_celery_beat"}',
        "solution": "",
    },
    {
        "category": "celery",
        "collect_type": "backend",
        "description": _("celery worker 任务执行测试"),
        "collect_metric": "celery.execution.status",
        "solution": "",
        "node_name": "celery",
        "metric_alias": "celery.execution.status",
        "collect_args": json.dumps(celery_queues_names),
    },
    {
        "category": "celery",
        "collect_type": "backend",
        "description": _("celery worker 进程状态"),
        "collect_metric": "celery.worker_process.status",
        "solution": "",
        "node_name": "celery",
        "metric_alias": "celery.process.status",
        "collect_args": '{"process_name": ['
        '"nodeman_celery_default","nodeman_celery_backend","nodeman_celery_backend_additional",'
        '"nodeman_pipeline_worker_00", "nodeman_pipeline_worker_01","nodeman_pipeline_schedule_00", '
        '"nodeman_pipeline_schedule_01", "nodeman_pipeline_additional"]}',
    },
]

supervisor_metrics = [
    {
        "category": "supervisor",
        "collect_type": "backend",
        "description": _("Supervisor 自身状态"),
        "collect_metric": "supervisor.status",
        "solution": "",
        "node_name": "supervisor",
        "metric_alias": "supervisor.status",
        "collect_args": "{}",
    },
    {
        "category": "supervisor",
        "collect_type": "backend",
        "description": _("Supervisor 进程状态"),
        "collect_metric": "supervisor.process.status",
        "solution": "",
        "node_name": "supervisor",
        "metric_alias": "supervisor.process.status",
        "collect_args": "{}",
    },
    {
        "category": "supervisor",
        "collect_type": "backend",
        "description": _("Supervisor 逃逸进程"),
        "collect_metric": "supervisor.escaped",
        "solution": "",
        "node_name": "supervisor",
        "metric_alias": "supervisor.escaped",
        "collect_args": '{"python_bin": "{{settings.PYTHON_BIN}}"}',
    },
]
node_metrics = redis_metrics + mysql_metrics + rabbitmq_metrics + celery_metrics + supervisor_metrics
HEALTHZ_NODE_METRICS = node_metrics


def init_healthz_node_metric():
    healthz_metrics_configs = []
    for metric in HEALTHZ_NODE_METRICS:
        newmetric = copy.deepcopy(metric)
        for field in metric:
            if field not in HEALTHZ_FIELD_NAMES:
                newmetric.pop(field)
        if newmetric["metric_alias"].endswith("status") and not newmetric["solution"]:
            newmetric["solution"] = json.dumps(
                [
                    {
                        "reason": _("进程：%s未启动或连接不上") % newmetric["node_name"],
                        "solution": _("确保进程：%s状态正常") % newmetric["node_name"],
                    }
                ]
            )
        healthz_metrics_configs.append({"metric_alias": metric["metric_alias"], **newmetric})
    return healthz_metrics_configs
