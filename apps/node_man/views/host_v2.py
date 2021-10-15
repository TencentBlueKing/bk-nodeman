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
from typing import Any, Dict, List

from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man import constants, models, tools
from apps.node_man.handlers.host_v2 import HostV2Handler
from apps.node_man.serializers import host_v2
from apps.utils import concurrent


class HostV2ViewSet(ModelViewSet):
    model = models.Host

    @action(detail=False, methods=["POST"], serializer_class=host_v2.HostSearchSerializer)
    def search(self, request):
        """
        @api {POST} /v2/host/search/ 查询主机列表
        @apiName list_host
        @apiGroup Host_v2
        @apiParam {Int[]} [bk_biz_id] 业务ID
        @apiParam {Int[]} [bk_host_id] 主机ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status, version, bk_cloud_id, node_from <br>
        query: IP、操作系统、Agent状态、Agent版本、云区域 单/多模糊搜索 <br>
        topology: 拓扑搜索，传入bk_set_ids, bk_module_ids
        @apiParam {List} [nodes] 拓扑节点, 例如：[{"bk_biz_id": 1, "bk_inst_id": 10, "bk_obj_id": "module"}, ...]
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {Int} [page] 当前页数，默认为`1`
        @apiParam {Int} [pagesize] 分页大小，默认为`10`，`-1` 表示跨页全选
        @apiParam {Boolean} [agent_status_count] 仅返回Agent统计状态，默认`False`
        @apiSuccessExample {json} 成功返回:
        {
            "total": 1,
            "list": [
                {
                    "bk_cloud_id": 1,
                    "bk_cloud_name": "云区域名称",
                    "bk_biz_id": 2,
                    "bk_biz_name": "业务名称",
                    "bk_host_id": 1,
                    "os_type": "linux",
                    "inner_ip": "127.0.0.1",
                    "status": "RUNNING",
                }
            ]
        }
        // 返回Agent状态信息
        {
            "total": 22,        // 总数
            "RUNNING": 10,      // 唯一表示正常的状态，异常Agent数 = result["total"] - result["RUNNING"]
            "UNKNOWN": 2,
            "TERMINATED": 2,
            "NOT_INSTALLED": 4,
            "UNREGISTER": 4
        }
        """
        query_params = self.validated_data
        return Response(
            HostV2Handler.list(params=query_params, return_all_node_type=query_params["return_all_node_type"])
        )

    @action(detail=False, methods=["POST"], serializer_class=host_v2.HostAgentStatusSerializer)
    def agent_status(self, request):
        """
        @api {POST} /v2/host/agent_status/ 统计给定拓扑节点的agent状态统计
        @apiName nodes_agent_status
        @apiGroup Host_v2
        @apiParam {List} [nodes] 拓扑节点, 例如：[{"bk_biz_id": 1, "bk_inst_id": 10, "bk_obj_id": "module"}, ...]
        @apiParam {String} [action] 权限类型，默认为agent_view
        @apiSuccessExample {json} 成功返回：
        [
            {
                "bk_biz_id": 1,
                "bk_inst_id": 10,
                "bk_obj_id": "module",
                "agent_status_count": {
                    "total": 22,        // 总数
                    "RUNNING": 10,      // 唯一表示正常的状态，异常Agent数 = result["total"] - result["RUNNING"]
                    "TERMINATED": 2,
                    "NOT_INSTALLED": 4,
                }
            },
        ]
        """
        return Response(
            HostV2Handler.agent_status(nodes=self.validated_data["nodes"], action=self.validated_data["action"])
        )

    @action(detail=False, methods=["POST"], serializer_class=host_v2.NodeCountSerializer)
    def node_statistic(self, request):
        """
        @api {POST} /v2/host/node_statistic/ 统计给定拓扑节点的主机数量
        @apiName node_statistic
        @apiGroup Host_v2
        @apiParam {List} [nodes] 拓扑节点, 例如：[{"bk_biz_id": 1, "bk_inst_id": 10, "bk_obj_id": "module"}, ...]
        @apiParam {String} [action] 权限类型，默认为agent_view
        @apiSuccessExample {json} 成功返回：
        [
            {
                "bk_biz_id": 2,
                "bk_obj_id": "biz",
                "bk_inst_id": 2,
                "host_count": 51
            },
            {
                "bk_biz_id": 3,
                "bk_obj_id": "biz",
                "bk_inst_id": 3,
                "host_count": 19
            }
        ]
        """

        nodes = self.validated_data["nodes"]
        iam_action = self.validated_data["action"]
        if not nodes:
            return Response([])

        params_list = [{"topo_node": node, "only_ids": False, "action": iam_action} for node in nodes]
        topo_node_with_host_ids_infos: List[Dict[str, Any]] = concurrent.batch_call(
            func=tools.HostV2Tools.list_host_ids_by_topo_node, params_list=params_list, get_data=lambda x: x
        )

        bk_inst_id__host_count_map = {
            host_count_info["bk_inst_id"]: len(host_count_info["bk_host_ids"])
            for host_count_info in topo_node_with_host_ids_infos
        }

        for node in nodes:
            if node["bk_obj_id"] == constants.CmdbObjectId.BIZ:
                node["bk_inst_id"] = node["bk_biz_id"]
            node["host_count"] = bk_inst_id__host_count_map.get(node["bk_inst_id"], 0)

        return Response(nodes)
