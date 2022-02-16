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
import time
from typing import Any, Dict

import ujson as json

from apps.backend.constants import REDIS_INSTALL_CALLBACK_KEY_TPL
from apps.backend.utils.redis import REDIS_INST
from apps.node_man import constants

from .base import ViewBaseTestCase


class ReportLogTestCase(ViewBaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        # 每个 case 执行前移除 redis 日志列表
        REDIS_INST.delete(self.gen_redis_list_key())

    def tearDown(self) -> None:
        super().tearDown()
        REDIS_INST.delete(self.gen_redis_list_key())

    def gen_redis_list_key(self) -> str:
        return REDIS_INSTALL_CALLBACK_KEY_TPL.format(sub_inst_id=self.SUB_INST_ID)

    @classmethod
    def gen_log(cls) -> Dict[str, Any]:
        return {
            "timestamp": time.time(),
            "level": random.choice(["INFO", "ERROR", "WARNING"]),
            "step": random.choice(["setup_agent", "get_config", "check deploy status", "download"]),
            "log": " ".join(
                random.choices(
                    ["", "setup agent , extract, render config", "check port 65535, get_config", "check ip"],
                    k=random.randint(1, 5),
                )
            ),
            "status": random.choice(["FAILED", "SUCCESS", "RUNNING", "-"]),
        }

    def query_report_log(self) -> Dict[str, Any]:
        logs = [self.gen_log() for _ in range(random.randint(1, 5))]
        query_params = {"task_id": self.PIPELINE_ID, "token": self.gen_token(), "logs": logs}
        self.client.post(
            path="/backend/report_log/",
            data=query_params,
            format=None,
            content_type="application/x-www-form-urlencoded",
        )
        return query_params

    def test_ttl(self):
        """验证key的过期时间符合预期"""
        query_params = self.query_report_log()
        self.assertEqual(REDIS_INST.llen(self.gen_redis_list_key()), len(query_params["logs"]))
        self.assertTrue(REDIS_INST.ttl(self.gen_redis_list_key()) <= 2 * constants.TimeUnit.DAY)
        # 预估上面语句执行时间不超过一分钟，验证过期时间下限
        self.assertTrue(REDIS_INST.ttl(self.gen_redis_list_key()) > constants.TimeUnit.DAY - constants.TimeUnit.MINUTE)

    def test_extend(self):
        """验证日志叠加"""
        first_query_params = self.query_report_log()
        second_query_params = self.query_report_log()

        self.assertEqual(
            len(first_query_params["logs"]) + len(second_query_params["logs"]),
            REDIS_INST.llen(self.gen_redis_list_key()),
        )
        self.assertEqual(
            REDIS_INST.lrange(self.gen_redis_list_key(), 0, 0)[0].decode(encoding="utf-8"),
            json.dumps(second_query_params["logs"][-1]),
        )
