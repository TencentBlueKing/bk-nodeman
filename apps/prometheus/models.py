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

import typing

from django_prometheus.conf import NAMESPACE
from prometheus_client import Counter

jobs_by_op_type_operate_step = Counter(
    "django_app_jobs_by_operate_step",
    "Count of jobs by operate, step.",
    ["operate", "step"],
    namespace=NAMESPACE,
)


subscriptions_by_object_node_category = Counter(
    "django_app_subscriptions_by_object_node_category",
    "Count of subscriptions by object, node, category.",
    ["object", "node", "category"],
    namespace=NAMESPACE,
)


def export_job_prometheus_mixin():
    """任务模型埋点"""

    class Mixin:
        job_type: str = None
        task_id_list: typing.List[int] = None
        _origin_task_id_list: typing.List[int] = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._origin_task_id_list = self.task_id_list

        def unpacking_job_type(self) -> typing.Tuple[str, str]:
            if not self.job_type:
                return "default", "default"
            operate_untreated, step = self.job_type.rsplit("_", 1)
            operate = operate_untreated.replace("MAIN_", "")
            return operate, step

        def inc(self):
            operate, step = self.unpacking_job_type()
            jobs_by_op_type_operate_step.labels(operate, step).inc()

        def _do_insert(self, *args, **kwargs):
            self.inc()
            return super()._do_insert(*args, **kwargs)

    return Mixin


def export_subscription_prometheus_mixin():
    """任务模型埋点"""

    class Mixin:
        object_type: typing.Optional[str] = None
        node_type: typing.Optional[str] = None
        category: typing.Optional[str] = None

        def _do_insert(self, *args, **kwargs):
            subscriptions_by_object_node_category.labels(
                self.object_type, self.node_type, self.category or "subscription"
            ).inc()
            return super()._do_insert(*args, **kwargs)

    return Mixin
