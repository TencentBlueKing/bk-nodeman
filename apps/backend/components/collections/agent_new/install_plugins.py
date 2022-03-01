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

from typing import List

from django.conf import settings

from apps.node_man import constants, models
from apps.utils.batch_request import request_multi_thread
from common.api import NodeApi

from ..base import CommonData
from ..subsubscription import SubSubscriptionBaseService
from .base import AgentBaseService


class InstallPluginsService(SubSubscriptionBaseService, AgentBaseService):
    @staticmethod
    def create_subscriptions(common_data: CommonData) -> List[int]:
        plugins = models.GsePluginDesc.get_auto_launch_plugins()
        params_list = []
        for plugin in plugins:
            params_list.append(
                {
                    "params": {
                        "run_immediately": True,
                        "bk_username": settings.SYSTEM_USE_API_ACCOUNT,
                        "scope": {
                            "node_type": models.Subscription.NodeType.INSTANCE,
                            "object_type": models.Subscription.ObjectType.HOST,
                            "nodes": [{"bk_host_id": bk_host_id} for bk_host_id in common_data.bk_host_ids],
                        },
                        "steps": [
                            {
                                "id": plugin.name,
                                "type": "PLUGIN",
                                "config": {
                                    "job_type": constants.JobType.MAIN_INSTALL_PLUGIN,
                                    "plugin_name": plugin.name,
                                    "plugin_version": "latest",
                                    "config_templates": [
                                        {"name": "{}.conf".format(plugin.name), "version": "latest", "is_main": True}
                                    ],
                                },
                                "params": {"context": {}},
                            }
                        ],
                    }
                }
            )
        subscription_ids = request_multi_thread(
            NodeApi.create_subscription, params_list, get_data=lambda x: [x["subscription_id"]]
        )
        return subscription_ids
