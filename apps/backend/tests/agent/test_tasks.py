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

from apps.backend.agent.tasks import collect_log
from apps.backend.tests.components.collections.agent.utils import (
    BK_HOST_ID,
    AgentTestObjFactory,
    SshManMockClient,
)
from pipeline.log.models import LogEntry


class Collectlog(TestCase):
    def setUp(self):
        AgentTestObjFactory.init_db()

    @patch("apps.backend.agent.tasks.SshMan", SshManMockClient)
    def test_collect_log(self):
        NODE_ID = "node_id"
        collect_log(BK_HOST_ID, NODE_ID)
        log_result = list(LogEntry.objects.all().values_list(NODE_ID, flat=True))
        self.assertEqual(set(log_result), {NODE_ID})
