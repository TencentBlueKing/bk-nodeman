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

import typing

from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models

from .. import constants, types
from ..query import resource


class BaseHandler:
    @staticmethod
    def format2tree_node(node: types.ReadableTreeNode) -> types.TreeNode:
        return {
            "bk_obj_id": node["object_id"],
            "bk_inst_id": node["instance_id"],
            "bk_biz_id": node["meta"]["bk_biz_id"],
        }

    @staticmethod
    def get_meta_data(bk_biz_id: int) -> types.MetaData:
        return {"scope_type": constants.ScopeType.BIZ.value, "scope_id": str(bk_biz_id), "bk_biz_id": bk_biz_id}

    @classmethod
    def format_hosts(cls, untreated_host_infos: typing.List[types.HostInfo]) -> typing.List[types.FormatHostInfo]:
        """
        格式化主机信息
        :param untreated_host_infos: 尚未进行格式化处理的主机信息
        :return: 格式化后的主机列表
        """
        bk_biz_ids: typing.Set[int] = set()
        bk_cloud_ids: typing.Set[int] = set()
        for untreated_host_info in untreated_host_infos:
            bk_biz_ids.add(untreated_host_info["bk_biz_id"])
            bk_cloud_ids.add(untreated_host_info["bk_cloud_id"])

        biz_id__info_map: typing.Dict[int, typing.Dict] = {
            biz_info["bk_biz_id"]: biz_info
            for biz_info in resource.ResourceQueryHelper.fetch_biz_list(list(bk_biz_ids))
        }
        cloud_id__info_map: typing.Dict[int, typing.Dict] = {
            cloud_info["bk_cloud_id"]: cloud_info
            for cloud_info in node_man_models.Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values(
                "bk_cloud_id", "bk_cloud_name"
            )
        }
        # 补充直连区域
        cloud_id__info_map[node_man_constants.DEFAULT_CLOUD] = {
            "bk_cloud_id": node_man_constants.DEFAULT_CLOUD,
            "bk_cloud_name": node_man_constants.DEFAULT_CLOUD_NAME,
        }

        treated_host_infos: typing.List[types.HostInfo] = []
        for untreated_host_info in untreated_host_infos:
            treated_host_infos.append(
                {
                    "meta": BaseHandler.get_meta_data(untreated_host_info["bk_biz_id"]),
                    "host_id": untreated_host_info["bk_host_id"],
                    "agent_id": untreated_host_info["bk_agent_id"],
                    "ip": untreated_host_info["inner_ip"],
                    "ipv6": untreated_host_info["inner_ipv6"],
                    "host_name": untreated_host_info["bk_host_name"],
                    "os_name": node_man_constants.OS_CHN.get(
                        untreated_host_info["os_type"], untreated_host_info["os_type"]
                    ),
                    "os_type": node_man_constants.OS_CHN.get(
                        untreated_host_info["os_type"], untreated_host_info["os_type"]
                    ),
                    # TODO 实时获取状态
                    "alive": (constants.AgentStatusType.NO_ALIVE.value, constants.AgentStatusType.ALIVE.value)[
                        untreated_host_info["status"] == node_man_constants.ProcStateType.RUNNING
                    ],
                    "cloud_area": {
                        "id": untreated_host_info["bk_cloud_id"],
                        "name": cloud_id__info_map.get(untreated_host_info["bk_cloud_id"], {}).get(
                            "bk_cloud_name", untreated_host_info["bk_cloud_id"]
                        ),
                    },
                    "biz": {
                        "id": untreated_host_info["bk_biz_id"],
                        "name": biz_id__info_map.get(untreated_host_info["bk_biz_id"], {}).get(
                            "bk_biz_name", untreated_host_info["bk_biz_id"]
                        ),
                    },
                }
            )

        return treated_host_infos
