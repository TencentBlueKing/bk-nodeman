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
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.iam import ActionEnum, Permission
from apps.iam.exceptions import PermissionDeniedError
from apps.iam.handlers import resources
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.serializers import cmdb


class CmdbViews(APIViewSet):
    @action(detail=False, serializer_class=cmdb.BizSerializer)
    def biz(self, request, *args, **kwargs):
        """
        @api {GET} /cmdb/biz/  查询用户所有业务
        @apiName retrieve_biz
        @apiGroup cmdb
        @apiParam {String="agent_view", "agent_operate", "proxy_operate",
        "plugin_view", "plugin_operate", "task_history_view"} action 操作类型
        @apiSuccessExample {json} 成功返回:
        [{
            "bk_biz_id": "50",
            "bk_biz_name": "蓝鲸XX"
        }]
        """

        data_list = CmdbHandler().biz(self.validated_data)
        return Response(data_list)

    @action(detail=False, methods=["GET"], serializer_class=cmdb.FetchTopoSerializer)
    def fetch_topo(self, request, *args, **kwargs):
        """
        @api {GET} /cmdb/fetch_topo/ 获得拓扑信息
        @apiName fetch_topo
        @apiGroup cmdb
        @apiParam {Int} bk_biz_id 主机ID，可选不传业务返回所有业务topo
        @apiSuccessExample {json} 成功返回:
        {
            "name": "蓝鲸",
            "id": 2,
            "biz_inst_id": "2-2",
            "type": "biz",
            "children": [
                {
                    "name": "空闲机池",
                    "id": 20,
                    "biz_inst_id": "2-20",
                    "type": "set",
                    "children": [
                        {"id": 3, "name": "空闲机", "type": "module", "children": []},
                        {"id": 4, "name": "故障机", "type": "module", "children": []},
                    ],
                },
                {
                    "name": "Tun",
                    "id": 10216,
                    "biz_inst_id": "2-10216",
                    "type": "yun",
                    "children": [
                        {
                            "name": "1",
                            "id": 128,
                            "biz_inst_id": "2-128",
                            "type": "set",
                            "children": [{"name": "job", "id": 260, "type": "module", "children": []}],
                        }
                    ],
                },
            ],
        }
        """
        data = self.validated_data

        # 返回用户具有权限的业务的业务拓扑列表
        bk_biz_id = data.get("bk_biz_id")
        if not bk_biz_id:
            return Response(CmdbHandler().fetch_all_topo())
        # 用户有权限获取的业务
        # 格式 { bk_biz_id: bk_biz_name , ...}
        iam_action = data.get("action", ActionEnum.AGENT_VIEW.id)
        user_biz = CmdbHandler().biz_id_name({"action": data.get("action", ActionEnum.AGENT_VIEW.id)})

        if not user_biz.get(bk_biz_id):
            iam_resources = [resources.Business.create_instance(bk_biz_id)]
            apply_data, apply_url = Permission().get_apply_data([iam_action], iam_resources)
            raise PermissionDeniedError(action_name=iam_action, apply_url=apply_url, permission=apply_data)

        return Response(CmdbHandler().fetch_topo(bk_biz_id))

    @action(detail=False, methods=["GET"], serializer_class=cmdb.CmdbSearchTopoSerializer)
    def search_topo(self, request):
        """
        @api {GET} /cmdb/search_topo/  查询拓扑
        @apiName search_topo
        @apiGroup cmdb
        @apiParam {String} kw 搜索关键字
        @apiParam {Int[]} [bk_biz_ids] 业务ID列表，可不传业务，搜索用户所拥有权限的全部业务
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiParamExample {json} 请求参数:
        [{
            "kw": "p"
        }]
        @apiSuccessExample {json} 成功返回:
        {
            "total": 3,
            "nodes": [
                {"name": "pbiz", "id": 12, "type": "biz", "path": "pbiz"},
                {"name": "p2", "id": 123, "type": "set", "path": "pbiz / p2"},
                {"name": "p4", "id": 1324, "type": "set", "path": "pbiz / p4"},
            ],
            "use_cache": True
        }
        """
        return Response(CmdbHandler().search_topo_nodes(self.validated_data))

    @action(detail=False, methods=["GET"], serializer_class=cmdb.CmdbSearchTopoSerializer)
    def search_ip(self, request):
        """
        @api {GET} /cmdb/search_ip/  查询IP
        @apiName search_ip
        @apiGroup cmdb
        @apiParam {String} kw 搜索IP关键字
        @apiParam {Int[]} [bk_biz_ids] 业务ID列表，可不传业务，搜索用户所拥有权限的全部业务
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiParamExample {json} 请求参数:
        [{
            "kw": "p"
        }]
        @apiSuccessExample {json} 成功返回:
        {
            "total": 2,
            "nodes": [
            {
                "bk_biz_id": 14,
                "bk_host_id": 221442,
                "bk_cloud_id": 0,
                "inner_ip": "1.1.1.1",
                "os_type": "LINUX",
                "bk_cloud_name": "直连区域",
                "status": "UNREGISTER"
            },
            {
                "bk_biz_id": 14,
                "bk_host_id": 221430,
                "bk_cloud_id": 0,
                "inner_ip": "2.2.2.2",
                "os_type": "LINUX",
                "bk_cloud_name": "直连区域",
                "status": "UNREGISTER"
            }
            ],
        }
        """
        return Response(CmdbHandler().search_ip(self.validated_data))

    @action(detail=False, methods=["GET"], serializer_class=cmdb.FetchBizServiceTemplateSerializer)
    def service_template(self, request, *args, **kwargs):
        """
        @api {GET} /cmdb/service_template/  查询服务模板列表
        @apiName service_template
        @apiGroup cmdb
        @apiParam {Int} bk_biz_id 业务ID
        @apiParamExample {json} 请求参数:
        {
            "bk_biz_id": 2
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                id: 68,
                name: "db模板",
            },
            {
                bk_biz_id: 2,
                id: 65,
                name: "服务模板名称",
            },
        ]
        """
        return Response(CmdbHandler().get_biz_service_template(self.validated_data["bk_biz_id"]))
