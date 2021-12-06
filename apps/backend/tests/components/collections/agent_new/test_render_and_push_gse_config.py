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
import base64

from apps.backend.components.collections.agent_new import components
from apps.backend.views import generate_gse_config
from apps.node_man import constants
from common.api import JobApi

from . import base


class RenderAndPushGseConfigTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "渲染并下发Agent配置成功"

    def component_cls(self):
        return components.RenderAndPushGseConfigComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record

        # 该接口仅调用一次
        self.assertEqual(len(record[JobApi.push_config_file]), 1)
        push_config_file_query_params = record[JobApi.push_config_file][0].args[0]

        # 仅下发一个配置文件
        self.assertEqual(len(push_config_file_query_params["file_list"]), 1)
        config_info = push_config_file_query_params["file_list"][0]

        self.assertEqual(push_config_file_query_params["file_target_path"], "/usr/local/gse/agent/etc")

        config_content = base64.b64decode(config_info["content"]).decode()
        for host in self.obj_factory.host_objs:
            node_type = ("agent", "proxy")[host.os_type == constants.NodeType.PROXY]
            except_content = generate_gse_config(host=host, filename=config_info["file_name"], node_type=node_type)
            self.assertEqual(except_content, config_content)
        super().tearDown()
