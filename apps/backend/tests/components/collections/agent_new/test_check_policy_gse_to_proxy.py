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
import copy
from typing import Dict

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from apps.backend.components.collections.agent_new import (
    check_policy_gse_to_proxy,
    components,
)
from apps.mock_data import common_unit
from apps.node_man import constants, models
from common.api import JobApi
from env.constants import GseVersion

from . import base


class CheckPolicyGseToProxyTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "检测 GSE Server 到 Proxy 策略成功"

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        host = models.Host.objects.all()[0]
        models.AccessPoint.objects.all().update(
            btfileserver={"inner_ip_infos": [{"ip": host.inner_ip}], "outer_ip_infos": [{"ip": host.outer_ip}]}
        )
        host_data = copy.deepcopy(common_unit.host.HOST_MODEL_DATA)
        host_data.update({"bk_host_id": cls.obj_factory.RANDOM_BEGIN_HOST_ID + cls.obj_factory.total_host_num})
        cls.obj_factory.bulk_create_model(models.Host, [host_data])

    def component_cls(self):
        return components.CheckPolicyGseToProxyComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        host_key__script_content_map: Dict[str, str] = {}
        # 建立主机 - 脚本内容的映射
        for call_record in record[JobApi.fast_execute_script]:
            query_params = call_record.args[0]
            script_content = base64.b64decode(call_record.args[0]["script_content"]).decode()
            if query_params["target_server"].get("host_id_list"):
                ip_list = [
                    {"bk_cloud_id": host.bk_cloud_id, "ip": host.inner_ip}
                    for host in models.Host.objects.filter(bk_host_id__in=query_params["target_server"]["host_id_list"])
                ]
            else:
                ip_list = query_params["target_server"]["ip_list"]

            for ip_info in ip_list:
                host_key__script_content_map[f"{ip_info['bk_cloud_id']}-{ip_info['ip']}"] = script_content

        # 检查渲染的脚本内容是否符合预期
        for host in self.obj_factory.host_objs:
            ap = host.ap
            port_config = ap.port_config
            btsvr_thrift_port = port_config.get("btsvr_thrift_port")
            for inner_host in ap.file_endpoint_info.inner_hosts:
                host_key = f"{constants.DEFAULT_CLOUD}-{inner_host}"
                self.assertEqual(
                    host_key__script_content_map[host_key],
                    check_policy_gse_to_proxy.REACHABLE_SCRIPT_TEMPLATE
                    % {
                        "proxy_ip": host.outer_ip or host.outer_ipv6,
                        "btsvr_thrift_port": port_config.get("btsvr_thrift_port"),
                        "bt_port": (port_config.get("bt_port"), btsvr_thrift_port)[settings.BKAPP_ENABLE_DHCP],
                        "tracker_port": (port_config.get("tracker_port"), btsvr_thrift_port)[
                            settings.BKAPP_ENABLE_DHCP
                        ],
                        "msg": _("请检查出口IP是否正确或策略是否开通"),
                    },
                )
        super().tearDown()


class Agent2TestCase(CheckPolicyGseToProxyTestCase):
    OVERWRITE_OBJ__KV_MAP = {
        settings: {
            "BKAPP_ENABLE_DHCP": True,
        },
    }

    def structure_common_inputs(self):
        inputs = super().structure_common_inputs()
        inputs["meta"] = {"GSE_VERSION": GseVersion.V2.value}
        return inputs

    @classmethod
    def get_default_case_name(cls) -> str:
        return "(Proxy 2.0) 检测 GSE Server 到 Proxy 策略成功"
