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

import random

import mock

from apps.backend.agent.tools import gen_batch_encrypt_token
from apps.mock_data import common_unit
from apps.node_man import models
from apps.utils.unittest.testcase import CustomAPITestCase


class ViewBaseTestCase(CustomAPITestCase):
    PIPELINE_ID = "03502d112bf1416d8584f179edf86bd1"
    SUB_INST_ID = random.randint(1, 10000)
    SUB_ID = random.randint(1, 10000)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        mock.patch("apps.backend.views.json.loads", lambda x: eval(x)).start()

    def gen_token(self, host: models.Host) -> str:

        return gen_batch_encrypt_token(
            hosts=[host],
            pipeline_id=self.PIPELINE_ID,
            sub_id=self.SUB_ID,
            host_id_sub_inst_id_map={common_unit.host.DEFAULT_HOST_ID: self.SUB_INST_ID},
        )
