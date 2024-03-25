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
from typing import Any, Dict, List, Optional, Union

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models
from env.constants import GseVersion

from ..base import CommonData
from ..common.script_content import REACHABLE_SCRIPT_TEMPLATE
from .base import AgentCommonData, AgentExecuteScriptService


class CheckPolicyGseToProxyService(AgentExecuteScriptService):
    @property
    def script_name(self):
        return "is_target_reachable"

    def get_target_servers(
        self, data, common_data: CommonData, host: models.Host
    ) -> Dict[str, Union[List[Dict[str, Any]], List[int]]]:
        # 取接入点
        host_ap: Optional[models.AccessPoint] = self.get_host_ap(common_data=common_data, host=host)
        if not host_ap:
            return {}
        file_endpoint_host_ids = models.Host.objects.filter(
            Q(bk_cloud_id=constants.DEFAULT_CLOUD, bk_addressing=constants.CmdbAddressingType.STATIC.value)
            & (
                Q(inner_ip__in=host_ap.file_endpoint_info.inner_hosts)
                | Q(inner_ipv6=host_ap.file_endpoint_info.inner_hosts)
            )
        ).values_list("bk_host_id", flat=True)

        return {
            "ip_list": [
                {
                    "bk_cloud_id": constants.DEFAULT_CLOUD,
                    "ip": inner_host,
                }
                for inner_host in host_ap.file_endpoint_info.inner_hosts
            ],
            "host_id_list": list(file_endpoint_host_ids),
        }

    def get_script_content(self, data, common_data: AgentCommonData, host: models.Host) -> str:
        host_ap: Optional[models.AccessPoint] = self.get_host_ap(common_data=common_data, host=host)
        if not host_ap:
            return ""

        port_config = host_ap.port_config
        btsvr_thrift_port = port_config.get("btsvr_thrift_port")

        gse_version = data.get_one_of_inputs("meta", {}).get("GSE_VERSION")

        return REACHABLE_SCRIPT_TEMPLATE % {
            "proxy_ip": host.outer_ip or host.outer_ipv6,
            "btsvr_thrift_port": btsvr_thrift_port,
            # Agent 2.0 bt_port & tracker_port 不属于 Proxy <> Server 的策略
            # 在上述情况下冗余探测 btsvr_thrift_port
            # Refer: https://github.com/TencentBlueKing/bk-nodeman/issues/1239
            "bt_port": (port_config.get("bt_port"), btsvr_thrift_port)[gse_version == GseVersion.V2.value],
            "tracker_port": (port_config.get("tracker_port"), btsvr_thrift_port)[gse_version == GseVersion.V2.value],
            "msg": _("请检查出口IP是否正确或策略是否开通"),
        }

    def _execute(self, data, parent_data, common_data: AgentCommonData):

        for sub_inst_id in common_data.subscription_instance_ids:
            gse_version = data.get_one_of_inputs("meta", {}).get("GSE_VERSION")
            bk_host_id = common_data.sub_inst_id__host_id_map[sub_inst_id]
            host = common_data.host_id_obj_map[bk_host_id]
            host_ap: Optional[models.AccessPoint] = self.get_host_ap(common_data, host)
            if not host_ap:
                continue

            port_config = host_ap.port_config

            if gse_version == GseVersion.V2.value:
                port_polices: List[str] = [f"{port_config.get('btsvr_thrift_port')}(tcp)"]
            else:
                port_polices: List[str] = [
                    f"{port_config.get('btsvr_thrift_port')}(tcp)",
                    f"{port_config.get('bt_port')}-{port_config.get('tracker_port')}(tcp/udp)",
                ]

            self.log_info(
                sub_inst_id,
                _(
                    "请确保 GSE File Server 公网IP（{file_endpoints}）到 Proxy 出口IP（{proxy_outer_ip}）的 "
                    "{port_polices} 访问策略正常。\n"
                    "另外请注意：\n"
                    "1. 可执行 curl ipinfo.io 确认「出口IP」\n"
                    "2. 不支持多台 Proxy 使用同一个「出口IP」\n"
                    "3. 请保证「出口IP」固定不变"
                ).format(
                    file_endpoints=",".join(host_ap.file_endpoint_info.outer_hosts),
                    proxy_outer_ip=host.outer_ip or host.outer_ipv6,
                    port_polices=", ".join(port_polices),
                ),
            )

        return super()._execute(data, parent_data, common_data)
