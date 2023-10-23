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
import os
import time
from typing import Dict

from bk_monitor_report import MonitorReporter as Reporter
from celery.utils.nodenames import gethostname, host_format
from prometheus_client import generate_latest
from prometheus_client.parser import text_string_to_metric_families

# logger = logging.getLogger("bk-monitor-report")


class MonitorReporter(Reporter):
    def __init__(
        self,
        data_id: int,
        access_token: str,
        target: str,
        url: str,
        report_interval: int = 60,
        chunk_size: int = 500,
        proc_type: str = "",
        instance_tmpl: str = "",
    ):
        super().__init__(data_id, access_token, target, url, report_interval, chunk_size)
        self.proc_type = proc_type
        self.instance_tmpl = instance_tmpl

    def generate_addition_labels(self) -> Dict[str, str]:
        addition_labels: Dict[str, str] = {"hostname": gethostname()}
        if self.proc_type == "celery":
            # 进程可用变量：https://docs.celeryq.dev/en/stable/userguide/workers.html
            # 启动参数：https://docs.celeryq.dev/en/stable/reference/cli.html#cmdoption-celery-worker-n
            addition_labels["nodeman_instance"] = host_format(self.instance_tmpl)
        else:
            addition_labels["nodeman_instance"] = host_format(self.instance_tmpl, P=str(os.getpid()))
        return addition_labels

    def generate_chunked_report_data(self):
        timestamp = round(time.time() * 1000)

        addition_labels = self.generate_addition_labels()
        data = {"data_id": self.data_id, "access_token": self.access_token, "data": []}
        size = 0
        metrics_text = generate_latest(self.registry).decode("utf-8")
        for family in text_string_to_metric_families(metrics_text):
            for sample in family.samples:
                labels = sample.labels or {}
                # 补充维度
                labels.update(addition_labels)
                data["data"].append(
                    {
                        "metrics": {sample.name: sample.value},
                        "target": self.target,
                        "dimension": labels,
                        "timestamp": timestamp,
                    }
                )
                size += 1
                if size % self.chunk_size == 0:
                    yield data
                    data = {"data_id": self.data_id, "access_token": self.access_token, "data": []}

        if data["data"]:
            yield data
