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

from apps.core.concurrent.retry import RetryHandler
from apps.node_man import constants, models
from apps.utils.batch_request import request_multi_thread
from common.api import NodeApi
from common.api.exception import DataAPIException

from ..base import CommonData
from ..subsubscription import SubSubscriptionBaseService
from .base import AgentBaseService


class StopPluginsService(SubSubscriptionBaseService, AgentBaseService):
    @staticmethod
    @RetryHandler(interval=1, retry_times=1, exception_types=[DataAPIException])
    def call_create_subscription_api(params):
        return NodeApi.create_subscription(params)

    @classmethod
    def create_subscriptions(cls, common_data: CommonData) -> List[int]:

        running_processes = models.ProcessStatus.objects.filter(
            status=constants.ProcStateType.RUNNING,
            bk_host_id__in=common_data.bk_host_ids,
            proc_type=constants.ProcType.PLUGIN,
            is_latest=True,
        )

        host_ids_processes = {}
        for process in running_processes:
            if process.bk_host_id not in host_ids_processes:
                host_ids_processes[process.bk_host_id] = []
            host_ids_processes[process.bk_host_id].append(process)

        params_list = []
        for host_id, processes in host_ids_processes.items():
            for process in processes:
                params_list.append(
                    {
                        "params": {
                            "run_immediately": True,
                            "category": models.Subscription.CategoryType.ONCE,
                            "bk_username": settings.SYSTEM_USE_API_ACCOUNT,
                            "is_main": True,
                            "plugin_name": process.name,
                            "scope": {
                                "node_type": models.Subscription.NodeType.INSTANCE,
                                "object_type": models.Subscription.ObjectType.HOST,
                                "nodes": [{"bk_host_id": host_id}],
                            },
                            "steps": [
                                {
                                    "id": process.name,
                                    "type": "PLUGIN",
                                    "config": {
                                        "job_type": constants.JobType.MAIN_STOP_PLUGIN,
                                        "plugin_name": process.name,
                                        "plugin_version": process.version or "latest",
                                        "config_templates": [
                                            {
                                                "name": "{}.conf".format(process.name),
                                                "version": process.version or "latest",
                                                "is_main": True,
                                            }
                                        ],
                                    },
                                    "params": {"context": {}},
                                }
                            ],
                        }
                    }
                )
        subscription_ids = request_multi_thread(
            cls.call_create_subscription_api, params_list, get_data=lambda x: [x["subscription_id"]]
        )
        return subscription_ids
