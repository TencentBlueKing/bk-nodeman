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
import random

from apps.backend.constants import REDIS_AGENT_CONF_KEY_TPL
from apps.backend.utils.redis import REDIS_INST
from apps.backend.views import generate_gse_config
from apps.mock_data import common_unit
from apps.node_man import models

from .base import ViewBaseTestCase


class GetGseConfigTestCase(ViewBaseTestCase):

    host: models.Host = None
    redis_agent_conf_key: str = None

    @classmethod
    def setUpTestData(cls):

        super().setUpTestData()
        host_model_data = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
        host_model_data.update(bk_host_id=random.randint(1000, 10000))
        cls.host = models.Host.objects.create(**host_model_data)
        # 此类查询在单元测试中会有如下报错， 因此将数据预先查询缓存
        # TransactionManagementError "You can't execute queries until the end of the 'atomic' block" while using signals
        # 参考：https://stackoverflow.com/questions/21458387
        cls.ap = cls.host.ap
        cls.proxies = list(cls.host.proxies)
        cls.install_channel = cls.host.install_channel
        cls.redis_agent_conf_key = REDIS_AGENT_CONF_KEY_TPL.format(file_name="agent.conf", sub_inst_id=cls.SUB_INST_ID)

    def setUp(self) -> None:
        super().setUp()
        # 每个 case 执行前移除 redis 日志列表
        REDIS_INST.delete(self.redis_agent_conf_key)

    def query_get_gse_config(self):
        query_params = {
            "bk_cloud_id": self.host.bk_cloud_id,
            "filename": "agent.conf",
            "node_type": self.host.node_type.lower(),
            "inner_ip": self.host.inner_ip,
            "token": self.gen_token(),
        }
        config = self.client.post(
            path="/backend/get_gse_config/",
            data=query_params,
            format=None,
            content_type="application/json",
        )
        return config

    def test_get_by_cache(self):
        config = self.query_get_gse_config()
        REDIS_INST.set(
            name=self.redis_agent_conf_key,
            value=generate_gse_config(
                host=self.host,
                filename="agent.conf",
                node_type=self.host.node_type.lower(),
                ap=self.ap,
                proxies=self.proxies,
                install_channel=self.install_channel,
            ),
        )
        REDIS_INST.expire(name=self.redis_agent_conf_key, time=5)
        cached_config = self.query_get_gse_config()
        self.assertEqual(config, cached_config)
