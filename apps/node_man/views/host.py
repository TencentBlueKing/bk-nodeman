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

from apps.generic import ModelViewSet
from apps.iam import ActionEnum
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.node_man.handlers.permission import HostPermission
from apps.node_man.models import Host
from apps.node_man.serializers.host import (
    BizProxySerializer,
    HostSerializer,
    HostUpdateSerializer,
    ProxySerializer,
    RemoveSerializer,
)
from apps.utils.local import get_request_username


class HostViewSet(ModelViewSet):
    model = Host
    permission_classes = (HostPermission,)

    @action(detail=False, methods=["POST"], serializer_class=HostSerializer)
    def search(self, request):
        """
        @api {POST} /host/search/ 查询主机列表
        @apiName list_host
        @apiGroup Host
        @apiParam {Int[]} [bk_biz_id] 业务ID
        @apiParam {Int[]} [bk_host_id] 主机ID
        @apiParam {List} [condition] 搜索条件，支持os_type, ip, status <br>
        version, bk_cloud_id, node_from 和 模糊搜索query
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiParam {String[]} [extra_data] 额外信息, 如 ['identity_info', 'job_result', 'topology']
        @apiParam {Int} [page] 当前页数
        @apiParam {Int} [pagesize] 分页大小
        @apiParam {Boolean} [only_ip] 只返回IP
        @apiParam {Boolean} [running_count] 返回正在运行机器数量
        @apiSuccessExample {json} 成功返回:
        {
            "total": 188,
            "list": [
                {
                    "bk_cloud_id": 1,
                    "bk_cloud_name": "云区域名称",
                    "bk_biz_id": 2,
                    "bk_biz_name": "业务名称",
                    "bk_host_id": 1,
                    "os_type": "linux",
                    "inner_ip": "127.0.0.1",
                    "outer_ip": "127.0.0.2",
                    "login_ip": "127.0.0.3",
                    "data_ip": "127.0.0.4",
                    "status": "RUNNING",
                    "version": "1.1.0",
                    "ap_id": -1,
                    "identity_info": {},
                    "job_result": {
                        "job_id": 1,
                        "status": "FAILED",
                        "current_step": "下载安装包",
                    }
                }
            ]
        }
        """
        return Response(HostHandler().list(self.validated_data, get_request_username()))

    @action(detail=False, serializer_class=ProxySerializer)
    def proxies(self, request, *args, **kwargs):
        """
        @api {GET} /host/proxies/ 查询云区域的proxy列表
        @apiName retrieve_cloud_proxies
        @apiGroup Host
        @apiParam {Int} bk_cloud_id 云区域ID
        @apiSuccessExample {json} 成功返回:
        [{
            "bk_cloud_id": 1,
            "bk_host_id": 1,
            "inner_ip": "127.0.0.1",
            "outer_ip": "127.0.0.2",
            "login_ip": "127.0.0.3",
            "data_ip": "127.0.0.4",
            "status": "RUNNING",
            "version": "1.1.0",

            "account": "root",
            "auth_type": "PASSWORD",
            "port": 22,

            "ap_id": 1,
            "ap_name": "接入点名称"
        }]
        """
        proxies = HostHandler().proxies(self.validated_data["bk_cloud_id"])
        # 用户有proxy操作权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": ActionEnum.PROXY_OPERATE.id})
        for proxy in proxies:
            proxy["permissions"] = {"operate": proxy["bk_biz_id"] in user_biz}

        return Response(proxies)

    @action(detail=False, serializer_class=BizProxySerializer)
    def biz_proxies(self, request, *args, **kwargs):
        """
        @api {GET} /host/biz_proxies/ 查询业务下云区域的proxy集合
        @apiName retrieve_biz_proxies
        @apiGroup Host
        @apiParam {Int} bk_biz_id 业务ID
        @apiSuccessExample {json} 成功返回:
        [{
            "bk_cloud_id": 1,
            "bk_host_id": 1,
            "inner_ip": "127.0.0.1",
            "outer_ip": "",
            "login_ip": null,
            "data_ip": null,
            "bk_biz_id": 1
        }]
        """
        return Response(HostHandler().biz_proxies(self.validated_data["bk_biz_id"]))

    @action(detail=False, methods=["POST"], serializer_class=RemoveSerializer)
    def remove_host(self, request, *args, **kwargs):
        """
        @api {POST} /host/remove_host/ 移除主机
        @apiDescription
        成功删除的host_id会在返回结果的success字段中。<br>
        如果需要删除的host_id不存在在数据库中，则会出现在fail字段中。<br>
        非跨页全选仅需传bk_host_id，跨页全选则不需要传bk_host_id。<br>
        此外：<br>
        如果is_proxy为true，则只针对Proxy做删除；<br>
        如果is_proxy为false，则只针对AGENT和PAGENT做删除。<br>
        bk_host_id，exclude_hosts 必填一个。<br>
        若填写了 exclude_hosts ，则代表跨页全选模式。<br>
        注意, 云区域ID、业务ID等筛选条件，仅在跨页全选模式下有效。<br>
        @apiName remove_host
        @apiGroup Host
        @apiParam {Int[]} [bk_host_id] 主机ID列表
        @apiParam {Boolean} is_proxy 是否针对Proxy的删除
        @apiParam {String} [bk_biz_id] 业务ID
        @apiParam {List} [conditions] 搜索条件，支持os_type, ip, status <br>
        version, bk_cloud_id, node_from 和 模糊搜索query
        @apiParam {Int[]} [exclude_hosts] 跨页全选排除主机
        @apiSuccessExample {json} 成功返回:
        {
            "success": [
                6121
            ],
            "fail": []
        }
        """
        return Response(HostHandler().remove_host(self.validated_data))

    @action(detail=False, methods=["POST"], serializer_class=HostUpdateSerializer)
    def update_single(self, request):
        """
        @api {POST} /host/update_single/ 更新Proxy主机信息
        @apiName update_host
        @apiGroup Host
        @apiParam {Int} bk_host_id 主机ID
        @apiParam {Number} [bk_cloud_id] 云区域ID
        @apiParam {String} [inner_ip] 内网IP
        @apiParam {String} [outer_ip] 外网IP
        @apiParam {String} [login_ip] 登录IP
        @apiParam {String} [data_ip] 数据IP
        @apiParam {String} [account] 账户名
        @apiParam {Int} [ap_id] 接入点ID
        @apiParam {Number} [port] 端口
        @apiParam {String} [auth_type] 认证类型
        @apiParam {String} [password] 密码
        """
        return Response(HostHandler().update_proxy_info(self.validated_data))
