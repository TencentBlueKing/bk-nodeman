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

from django_prometheus.conf import NAMESPACE
from prometheus_client import Counter

from apps.node_man import constants

job_model_updates = Counter(
    "django_job_model_updates_total",
    "Number of update operations by model.",
    ["job_type", "status"],
    namespace=NAMESPACE,
)


def export_job_prometheus_mixin():
    """任务模型埋点"""

    class Mixin:
        _original_status = None
        status = None
        job_type = None

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._origin_status = self.status

        def _do_update(self, *args, **kwargs):
            # 任务状态有变更，且目标状态不是处理中的，则进行埋点
            if self._origin_status != self.status and self.status not in constants.JobStatusType.PROCESSING_STATUS:
                job_model_updates.labels(self.job_type, self.status).inc()
            return super()._do_update(*args, **kwargs)

    return Mixin
