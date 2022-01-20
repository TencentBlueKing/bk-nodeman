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
import base64
from typing import Dict

from django.utils.translation import ugettext_lazy as _

from apps.backend.components.collections.agent_new import (
    check_policy_gse_to_proxy,
    components,
)
from common.api import JobApi

from . import base


class CheckPolicyGseToProxyTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "检测 GSE Server 到 Proxy 策略成功"

    def component_cls(self):
        return components.CheckPolicyGseToProxyComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        host_key__script_content_map: Dict[str, str] = {}
        # 建立主机 - 脚本内容的映射
        for call_record in record[JobApi.fast_execute_script]:
            query_params = call_record.args[0]
            script_content = base64.b64decode(call_record.args[0]["script_content"]).decode()
            for ip_info in query_params["target_server"]["ip_list"]:
                host_key__script_content_map[f"{ip_info['bk_cloud_id']}-{ip_info['ip']}"] = script_content

        # 检查渲染的脚本内容是否符合预期
        for host in self.obj_factory.host_objs:
            host_key = f"{host.bk_cloud_id}-{host.inner_ip}"
            port_config = host.ap.port_config
            self.assertEqual(
                host_key__script_content_map[host_key],
                check_policy_gse_to_proxy.REACHABLE_SCRIPT_TEMPLATE
                % {
                    "proxy_ip": host.outer_ip,
                    "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
                    "bt_port": port_config.get("bt_port"),
                    "tracker_port": port_config.get("tracker_port"),
                    "msg": _("请检查数据传输IP是否正确或策略是否开通"),
                },
            )
        super().tearDown()
