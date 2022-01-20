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
from unittest.mock import patch

from django.test import TestCase

from apps.backend.healthz.processor import get_backend_healthz


class CheckerMockResult:
    @classmethod
    def as_json(cls):
        return '{"value": ""}'


def mock_check(*args, **kwargs):
    return CheckerMockResult()


class TestHealthz(TestCase):
    @patch("apps.backend.healthz.checker.checker.HealthChecker.check", mock_check)
    def test_process(self):
        metric_infos = get_backend_healthz()
        metric_result = [metric_info["metric_alias"] for metric_info in metric_infos]
        self.assertEqual(
            metric_result,
            [
                "redis.status",
                "redis.read.status",
                "redis.write.status",
                "database.status",
                "rabbitmq.status",
                "celery.beat.status",
                "celery.execution.status",
                "celery.process.status",
                "supervisor.status",
                "supervisor.process.status",
                "supervisor.escaped",
            ],
        )
