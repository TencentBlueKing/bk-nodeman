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
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.handlers.network_strategy import NetworkStrategyHandler
from apps.node_man.serializers import network_strategy

NETWORK_STRATEGY_VIEW_TAGS = ["network_strategy"]


class NetworkStrategyViews(APIViewSet):
    @swagger_auto_schema(
        operation_summary="云区域安装Agent策略",
        tags=NETWORK_STRATEGY_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=network_strategy.InstallAgentStrategySerializer)
    def install_agent_strategy(self, request, *args, **kwargs):
        """
        @api {POST} /network_strategy/install_agent_strategy/  云区域安装Agent策略
        @apiName install_agent_strategy
        @apiGroup NetworkStrategy
        @apiParam {List} agent_info Agent主机信息
        @apiParamExample {Json} 请求参数
        {
            "agent_info": [{"bk_cloud_id": 1, "inner_ip": "127.0.0.1"}],
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "name": "test-默认接入点1"
                "strategy_data": [
                    {
                        "source_address": "127.0.0.1",
                        "target_address": "127.0.0.2"
                        "port": "18625"
                        "protocol": "TCP"
                        "use": "数据服务端口"
                    }
                ]
            }
        ]
        """
        validated_data = self.validated_data
        return Response(NetworkStrategyHandler().install_agent_strategy(validated_data["agent_info"]))

    @swagger_auto_schema(
        operation_summary="云区域安装Proxy网络策略",
        tags=NETWORK_STRATEGY_VIEW_TAGS,
    )
    @action(detail=False, methods=["POST"], serializer_class=network_strategy.InstallProxyStrategySerializer)
    def install_proxy_strategy(self, request, *args, **kwargs):
        """
        @api {POST} /network_strategy/install_proxy_strategy/  云区域安装Agent策略
        @apiName install_proxy_strategy
        @apiGroup NetworkStrategy
        @apiParam {List} proxy_info Proxy主机信息
        @apiParamExample {Json} 请求参数
        {
            "agent_info": [{"bk_cloud_id": 1, "outer_ip": "127.0.0.1"}],
        }
        @apiSuccessExample {json} 成功返回:
        [
            {
                "name": "test-默认接入点2"
                "strategy_data": [
                    {
                        "source_address": "127.0.0.1",
                        "target_address": "127.0.0.2"
                        "port": "22"
                        "protocol": "TCP"
                        "use": "ssh连接"
                    }
                ]
            }
        ]
        """
        validated_data = self.validated_data
        return Response(NetworkStrategyHandler().install_proxy_strategy(validated_data["proxy_info"]))
