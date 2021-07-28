# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from unittest.mock import patch

from django.test import TestCase

from apps.node_man.handlers.healthz.handler import HealthzHandler
from apps.node_man.tests.utils import NodeApi


def check_result(*args, **kwargs):
    class result:
        @classmethod
        def as_json(cls):
            return '{"value": ""}'

    def check(*args, **kwargs):
        return result

    return check


class TestHealthz(TestCase):
    @patch("apps.node_man.handlers.healthz.handler.NodeApi.metric_list", NodeApi.metric_list)
    def test_process(self):
        result = HealthzHandler().list_metrics()
        metric_result = [info["metric_alias"] for info in result]
        self.assertEqual(metric_result, ["cmdb.status", "job.status", "nodeman.status", "gse.status"])
