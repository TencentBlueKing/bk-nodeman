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
from apps.node_man.handlers.debug import DebugHandler
from apps.node_man.handlers.permission import DebugPermission
from apps.node_man.serializers.debug import (
    HostDebugSerializer,
    SubscriptionDebugSerializer,
    TaskDebugSerializer,
)


class DebugViews(APIViewSet):
    """
    Debug 调试接口视图层
    """

    permission_classes = (DebugPermission,)

    @action(detail=False, methods=["GET"], serializer_class=SubscriptionDebugSerializer)
    def fetch_subscription_details(self, request, *args, **kwargs):
        """
        @api {GET} /debug/fetch_subscription_details/  查询订阅任务详情
        @apiName fetch_subscription_details
        @apiGroup debug
        @apiParam {int} subscription_id 订阅任务ID
        @apiSuccessExample {json} 成功返回:
        [
            {
                "task_id": 497,
                "task_scope": {
                    "nodes": [
                        {
                            "bk_host_id": 9640
                        }
                    ],
                    "bk_biz_id": null,
                    "node_type": "INSTANCE",
                    "object_type": "HOST",
                    "need_register": false
                },
                "task_actions": {
                    "host|instance|host|9640": {
                        "agent": "REINSTALL_AGENT"
                    }
                },
                "is_auto_trigger": false,
                "create_time": "2020-07-29 16:35:41+0800",
                "details": "https://__domain__/o/bk_nodeman/api/debug/
                            get_task_detail?subscription_id=362&task_id=497"
            }
        ]
        """

        data_list = DebugHandler().subscription_details(self.validated_data["subscription_id"])
        return Response(data_list)

    @action(detail=False, methods=["GET"], serializer_class=TaskDebugSerializer)
    def fetch_task_details(self, request, *args, **kwargs):
        """
        @api {GET} /debug/fetch_task_details/  查询任务执行详情
        @apiName fetch_task_details
        @apiGroup debug
        @apiParam {int} subscription_id 订阅任务ID
        @apiParam {int} task_id 任务ID
        @apiSuccessExample {json} 成功返回:
        [
            {
                "subscription_id": 16,
                "task_id": 26,
                "instance_id": "host|instance|host|1024",
                "logs": [
                    {
                        "step": "选择接入点",
                        "status": "SUCCESS",
                        "log": "[2020-03-28 18:10:38 INFO] 开始选择接入点\n[2020-03-28 18:10:38 INFO] 当前主机已分配接入点[默认接入点]",
                        "start_time": "2020-03-28 10:10:38",
                        "finish_time": "2020-03-28 10:10:38"
                    },
                    {
                        "step": "安装",
                        "status": "FAILED",
                        "log": "",
                        "start_time": "2020-03-28 10:10:38",
                        "finish_time": "2020-03-28 10:11:25"
                    },
                    {
                        "step": "查询Agent状态",
                        "status": "PENDING",
                        "log": "",
                        "start_time": null,
                        "finish_time": null
                    },
                    {
                        "step": "更新任务状态",
                        "status": "PENDING",
                        "log": "",
                        "start_time": null,
                        "finish_time": null
                    }
                ],
                "create_time": "2020-03-28 18:10:36+0800",
                "update_time": "2020-03-28 18:10:36+0800",
                "is_latest": true
            }
        ]
        """
        data_list = DebugHandler().task_details(self.validated_data["subscription_id"], self.validated_data["task_id"])
        return Response(data_list)

    @action(detail=False, methods=["GET"], serializer_class=SubscriptionDebugSerializer)
    def fetch_hosts_by_subscription(self, request, *args, **kwargs):
        """
        @api {GET} /debug/fetch_hosts_by_subscription/  查询订阅任务下的主机
        @apiName fetch_hosts_by_subscription
        @apiGroup debug
        @apiParam {int} subscription_id 订阅任务ID
        @apiSuccessExample {json} 成功返回:
        {
            "total": 2,
            "list": [
                {
                    "bk_host_id": 9640,
                    "bk_biz_id": 6,
                    "bk_cloud_id": 0,
                    "inner_ip": "127.0.0.1",
                    "os_type": "LINUX",
                    "node_type": "AGENT",
                    "plugin_status": [
                        {
                            "name": "gseagent",
                            "status": "UNKNOWN",
                            "version": ""
                        },
                        {
                            "name": "basereport",
                            "status": "UNKNOWN",
                            "version": ""
                        },
                        {
                            "name": "bkmetricbeat",
                            "status": "UNREGISTER",
                            "version": ""
                        },
                        ... ...
                    ]
                },
            ]
        }
        """

        data_list = DebugHandler().fetch_hosts_by_subscription(self.validated_data["subscription_id"])
        return Response(data_list)

    @action(detail=False, methods=["GET"], serializer_class=HostDebugSerializer)
    def fetch_subscriptions_by_host(self, request, *args, **kwargs):
        """
        @api {GET} /debug/fetch_subscriptions_by_host/  查询主机涉及到的所有订阅任务
        @apiName fetch_subscriptions_by_host
        @apiGroup debug
        @apiParam {int} bk_host_id 主机ID
        @apiSuccessExample {json} 成功返回:
        [
            364,
            365
        ]
        """

        data_list = DebugHandler().fetch_subscriptions_by_host(self.validated_data["bk_host_id"])
        return Response(data_list)
