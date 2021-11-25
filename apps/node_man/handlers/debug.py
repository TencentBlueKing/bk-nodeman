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
from collections import defaultdict
from typing import Dict, List

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from apps.node_man.exceptions import HostNotExists
from apps.node_man.models import (
    Host,
    ProcessStatus,
    Subscription,
    SubscriptionInstanceRecord,
    SubscriptionTask,
)
from apps.utils import APIModel
from common.api import NodeApi


class DebugHandler(APIModel):
    """
    Debug处理器
    """

    @staticmethod
    def get_log(subscription_id: int, instance_id: str) -> Dict[str, List[Dict]]:
        """
        根据订阅任务ID，实例ID，获取日志
        :param subscription_id: 订阅任务ID
        :param instance_id: 实例ID
        :return: 日志列表
        """
        task_result_detail = NodeApi.get_subscription_task_detail(
            {"subscription_id": subscription_id, "instance_id": instance_id}
        )
        log_gby_sub_host_index = defaultdict(list)
        for step in task_result_detail.get("steps", []):
            for index, target_host_result_detail in enumerate(step.get("target_hosts", [])):
                logs = [
                    {
                        "step": sub_step.get("node_name"),
                        "status": sub_step["status"],
                        "log": sub_step["log"],
                        "start_time": sub_step.get("start_time"),
                        "finish_time": sub_step.get("finish_time"),
                    }
                    for sub_step in target_host_result_detail.get("sub_steps", {})
                ]
                log_gby_sub_host_index[f'{step["id"]}_{index}'] = logs
        return log_gby_sub_host_index

    def task_details(self, subscription_id, task_id) -> List[Dict]:
        """
        获得任务执行详情
        :param subscription_id: 订阅任务ID
        :param task_id: 任务ID
        :return: 任务执行详情，包括日志
        """

        instance_records = list(
            SubscriptionInstanceRecord.objects.filter(subscription_id=subscription_id, task_id=task_id).values(
                "subscription_id", "task_id", "instance_id", "create_time", "update_time", "is_latest"
            )
        )
        for instance_record in instance_records:
            instance_record["logs"] = self.get_log(subscription_id, instance_record["instance_id"])

        return instance_records

    def subscription_details(self, subscription_id):
        """
        获取指定订阅任务的详细信息
        :param subscription_id: 订阅任务ID
        :return: 订阅任务的详细信息
        """

        # 获取任务相关信息
        tasks = SubscriptionTask.objects.filter(subscription_id=subscription_id)
        task_info = []
        for task in tasks:
            task_temp_info = {
                "task_id": task.id,
                "task_scope": task.scope,
                "task_actions": task.actions,
                "is_auto_trigger": task.is_auto_trigger,
                "create_time": task.create_time,
                "details": f"{settings.BK_NODEMAN_HOST}/api/debug/fetch_task_details?"
                f"subscription_id={subscription_id}&task_id={task.id}",
            }

            task_info.append(task_temp_info)

        return task_info

    def fetch_hosts_by_subscription(self, subscription_id):
        """
        获取指定订阅任务下所有主机的所有插件信息
        :param subscription_id: 订阅任务ID
        :return: 订阅任务包含的所有主机的所有插件信息
        """

        # 获取任务相关信息
        subscription = Subscription.objects.get(id=subscription_id)

        bk_host_ids = []
        for node in subscription.nodes:
            # 获得所有bk_host_id.
            if "bk_host_id" in node:
                bk_host_ids.append(node["bk_host_id"])
            elif "bk_cloud_id" in node:
                hosts = Host.objects.filter(bk_cloud_id=node["bk_cloud_id"], inner_ip=node["ip"])
                bk_host_ids.extend([host.bk_host_id for host in hosts])

        # 获取所有插件状态
        host_plugin = {}
        plugins = ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids, source_type="default").values()
        for plugin in plugins:
            if host_plugin.get(plugin["bk_host_id"]):
                host_plugin[plugin["bk_host_id"]].append(
                    {"name": plugin["name"], "status": plugin["status"], "version": plugin["version"]}
                )
            else:
                host_plugin[plugin["bk_host_id"]] = [
                    {"name": plugin["name"], "status": plugin["status"], "version": plugin["version"]}
                ]

        # 获取所有主机状态
        hosts = list(
            Host.objects.filter(bk_host_id__in=bk_host_ids).values(
                "bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "os_type", "node_type"
            )
        )
        for host in hosts:
            host["plugin_status"] = host_plugin.get(host["bk_host_id"], [])

        result = {"total": len(hosts), "list": hosts}
        return result

    def fetch_subscriptions_by_host(self, bk_host_id):
        """
        获取主机所涉及到的所有订阅任务
        :param bk_host_id: 主机ID
        :return: 主机所涉及到的所有订阅任务
        """

        try:
            host = Host.objects.get(bk_host_id=bk_host_id)
        except ObjectDoesNotExist:
            raise HostNotExists("主机ID不存在")

        records_by_host_id = list(
            SubscriptionInstanceRecord.objects.filter(instance_id=f"host|instance|host|{bk_host_id}")
        )
        records_by_ip = list(
            SubscriptionInstanceRecord.objects.filter(
                instance_id=f"host|instance|host|{host.inner_ip}-{host.bk_cloud_id}-0"
            )
        )

        result = []
        for record in records_by_ip + records_by_host_id:
            result.append(
                {
                    "subscription_id": record.subscription_id,
                    "subscription_detail": f"{settings.BK_NODEMAN_HOST}/api/debug/fetch_subscription_details?"
                    f"subscription_id={record.subscription_id}",
                }
            )

        return result
