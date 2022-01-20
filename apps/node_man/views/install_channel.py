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
from rest_framework.response import Response

from apps.generic import ModelViewSet
from apps.node_man.handlers.install_channel import InstallChannelHandler
from apps.node_man.handlers.permission import InstallChannelPermission
from apps.node_man.models import InstallChannel
from apps.node_man.serializers.install_channel import BaseSerializer, UpdateSerializer


class InstallChannelViewSet(ModelViewSet):
    model = InstallChannel
    lookup_value_regex = "[0-9.]+"
    permission_classes = (InstallChannelPermission,)

    def list(self, request, *args, **kwargs):
        """
        @api {GET} /install_channel/ 查询安装通道列表
        @apiName list_install_channel
        @apiGroup InstallChannel
        @apiSuccessExample {json} 成功返回:
        [
            {
                "id": 1,
                "name": "安装通道名称",
                "bk_cloud_id": 0,
                "jump_servers": ["127.0.0.1"],
                "upstream_servers": {
                    "taskserver": ["127.0.0.1"],
                    "btfileserver": ["127.0.0.1"],
                    "dataserver": ["127.0.0.1"]
                }
            }
        ]
        """
        install_channels = InstallChannelHandler.list()
        return Response(install_channels)

    def create(self, request, *args, **kwargs):
        """
        @api {POST} /install_channel/  创建安装通道
        @apiName create_install_channel
        @apiGroup InstallChannel
        @apiParam {String} name 安装通道名称
        @apiParam {Int} bk_cloud_id 云区域ID
        @apiParam {List} jump_servers 跳板机节点
        @apiParam {Object} upstream_servers 上游节点
        @apiParamExample {Json} 请求参数
        {
            "name": "安装通道名称",
            "bk_cloud_id": 0,
            "jump_servers": ["127.0.0.1"],
            "upstream_servers": {
                "taskserver": ["127.0.0.1"],
                "btfileserver": ["127.0.0.1"],
                "dataserver": ["127.0.0.1"]
        }
        @apiSuccessExample {json} 成功返回:
        {
            "id": 1
        }
        """
        self.serializer_class = UpdateSerializer
        data = self.validated_data
        name = data["name"]
        bk_cloud_id = data["bk_cloud_id"]
        jump_servers = data["jump_servers"]
        upstream_servers = data["upstream_servers"]
        result = InstallChannelHandler(bk_cloud_id=bk_cloud_id).create(name, jump_servers, upstream_servers)
        return Response(result)

    def update(self, request, *args, **kwargs):
        """
        @api {PUT} /install_channel/{{pk}}/  编辑安装通道
        @apiName update_install_channel
        @apiGroup InstallChannel
        @apiParam {String} name 安装通道名称
        @apiParam {Int} bk_cloud_id 云区域ID
        @apiParam {List} jump_servers 跳板机节点
        @apiParam {Object} upstream_servers 上游节点
        @apiParamExample {Json} 请求参数
        {
            "name": "安装通道名称",
            "bk_cloud_id": 0,
            "jump_servers": ["127.0.0.1"],
            "upstream_servers": {
                "taskserver": ["127.0.0.1"],
                "btfileserver": ["127.0.0.1"],
                "dataserver": ["127.0.0.1"]
            }
        }
        """
        self.serializer_class = UpdateSerializer
        data = self.validated_data
        install_channel_id = int(kwargs["pk"])
        name = data["name"]
        bk_cloud_id = data["bk_cloud_id"]
        jump_servers = data["jump_servers"]
        upstream_servers = data["upstream_servers"]
        InstallChannelHandler(bk_cloud_id=bk_cloud_id).update(install_channel_id, name, jump_servers, upstream_servers)
        return Response({})

    def destroy(self, request, *args, **kwargs):
        """
        @api {DELETE} /install_channel/{{pk}}/  删除安装通道
        @apiName delete_install_channel
        @apiParam {Int} bk_cloud_id 云区域ID
        @apiGroup InstallChannel
        """
        self.serializer_class = BaseSerializer
        data = self.validated_data
        install_channel_id = int(kwargs["pk"])
        bk_cloud_id = data["bk_cloud_id"]
        InstallChannelHandler(bk_cloud_id=bk_cloud_id).destroy(install_channel_id)
        return Response({})
