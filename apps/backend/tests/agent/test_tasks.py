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
from typing import Optional, Type
from unittest.mock import patch

from apps.backend.agent.tasks import collect_log
from apps.backend.tests.components.collections.agent_new import utils
from apps.utils.unittest.testcase import CustomBaseTestCase
from pipeline.log.models import LogEntry


class CollectLogTestCase(CustomBaseTestCase):

    OBJ_FACTORY_CLASS: Type[utils.AgentTestObjFactory] = utils.AgentTestObjFactory

    obj_factory: Optional[utils.AgentTestObjFactory] = None

    @classmethod
    def setUpClass(cls):
        cls.obj_factory = cls.OBJ_FACTORY_CLASS()
        super().setUpClass()

    @classmethod
    def setUpTestData(cls):
        cls.obj_factory.init_db()
        super().setUpTestData()

    @patch("apps.backend.agent.tasks.SshMan", utils.SshManMockClient)
    def test_collect_log(self):
        node_id = "node_id"

        for host in self.obj_factory.host_objs:
            collect_log(host.bk_host_id, node_id)
            log_result = list(LogEntry.objects.all().values_list(node_id, flat=True))
            self.assertEqual(set(log_result), {node_id})
