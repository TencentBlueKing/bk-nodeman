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
import base64
from collections import defaultdict
from datetime import timedelta
from itertools import groupby
from operator import itemgetter
from typing import Dict, List, Union

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from apps.node_man import constants
from apps.node_man.exceptions import HostNotExists
from apps.node_man.models import (
    Host,
    ProcessStatus,
    Subscription,
    SubscriptionInstanceRecord,
    SubscriptionInstanceStatusDetail,
    SubscriptionTask,
)
from apps.node_man.periodic_tasks.utils import JobDemand
from apps.utils import APIModel, basic
from apps.utils.basic import filter_values
from common.api import JobApi, NodeApi


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

    def zombie_sub_inst_count(self, days: int):
        days = max(days, 1)
        days = min(days, 60)
        query_kwargs = {
            "update_time__range": (
                timezone.now() - timedelta(days=1),
                timezone.now() - timedelta(days),
            ),
            "status__in": [constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING],
        }

        count = SubscriptionInstanceRecord.objects.filter(**query_kwargs).count()
        return {"count": count}

    def track_host_info_by_log_keywords(self, start_time, end_time, keyword_list: List[str]):
        # 通过SubscriptionInstanceRecord 和 SubscriptionInstanceStatusDetail 找出在  start_time 和 end_time 之间的执行变更的主机记录
        # keyword_list: 关键词列表，主要是因为 Orm 不支持正则查询，所以需要通过关键词列表来进行查询
        # example: keyword_list=["开始 渲染下发配置", "external_plugins"]
        try:
            # 校验时间格式可以被 django 的 ORM 解析
            start_time = timezone.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_time = timezone.datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise ValueError("时间格式错误, 格式: %Y-%m-%d %H:%M:%S")
        # 校验时间范围，看下是否 start_time 早于 end_time
        if start_time > end_time:
            raise ValueError("时间范围错误, start_time 晚于 end_time")
        # 校验 regex 是否是合理的 re 格式
        time_scope_instance_ids = SubscriptionInstanceRecord.objects.filter(
            create_time__range=(start_time, end_time)
        ).values_list("id", flat=True)
        instance_detaile_query = [Q(log__contains=keyword) for keyword in keyword_list]

        instance_detaile_records = SubscriptionInstanceStatusDetail.objects.filter(*instance_detaile_query).filter(
            subscription_instance_record_id__in=time_scope_instance_ids,
            create_time__range=(start_time, end_time),
        )

        match_regex_instance_ids = [record.subscription_instance_record_id for record in instance_detaile_records]
        match_regex_instance_ids = list(set(match_regex_instance_ids))

        # 将匹配到的 instance_id 通过 SubscriptionInstanceRecord 的 id 找到对应的记录，并且通过其中的 instance_info 转换为具体的主机
        instance_records = SubscriptionInstanceRecord.objects.filter(
            id__in=match_regex_instance_ids, create_time__range=(start_time, end_time)
        )
        subscription_id__host_infos_map = defaultdict(list)
        for instance_record in instance_records:
            host_info = instance_record.instance_info["host"]
            subscription_id__host_infos_map[instance_record.subscription_id].append(
                {
                    "bk_host_id": host_info["bk_host_id"],
                    "bk_cloud_id": host_info["bk_cloud_id"],
                    "bk_biz_id": host_info.get("bk_biz_id"),
                    "inner_ip": host_info.get("bk_host_innerip"),
                    "inner_ipv6": host_info.get("bk_host_inneripv6"),
                }
            )
        statistical_result = defaultdict(list)
        for sub_id, host_infos in subscription_id__host_infos_map.items():
            statistical_result["subscription_ids"].append(sub_id)
            for host_info in host_infos:
                statistical_result["bk_host_ids"].append(host_info["bk_host_id"])
                inner_ip = host_info.get("inner_ip")
                inner_ipv6 = host_info.get("inner_ipv6")
                if inner_ip:
                    statistical_result["cloud_id__ip_list"].append(
                        f"{host_info['bk_cloud_id']}:{host_info['inner_ip']}"
                    )
                if inner_ipv6:
                    statistical_result["cloud_id__ipv6_list"].append(
                        f"{host_info['bk_cloud_id']}:{host_info['inner_ipv6']}"
                    )
                statistical_result["bk_host_ids"].append(host_info["bk_host_id"])
        statistical_result["subscription_id__host_infos_map"] = subscription_id__host_infos_map

        # 去除列表中的重复值
        for key, value in statistical_result.items():
            if isinstance(value, list):
                statistical_result[key] = list(set(value))
        return statistical_result

    def custom_distribute_job(
        self,
        script_content_map: Dict[str, str],
        host_info_list: List[Union[int, str]] = None,
        subscription_id__bk_host_infos_map: Dict[str, List[Union[int, Dict[str, int]]]] = None,
        script_param: str = "",
    ):
        """
        自定义分发脚本
        :param host_info_list: [11, 22, 33, 44] or ["0:127.0.0.1", "0:127.0.0.2"]
        :param subscription_id__bk_host_ids_info_map: {11: [{"bk_host_id": x, "ip": x,  "bk_cloud_id": x}...]}
        :param script_content_map: 脚本内容 {"bat": xxx, "shell": xxx}
        :param script_param: 脚本参数不区分操作系统
        :return: 任务ID
        """
        script_content_map = filter_values(script_content_map)
        # host_info_list 和 subscription_id__bk_host_ids_info_map 不能同时为空, 并且不能同时存在
        if host_info_list and subscription_id__bk_host_infos_map:
            raise ValueError("host_info_list 和 subscription_id__bk_host_ids_info_map 不能同时存在")
        if not host_info_list and not subscription_id__bk_host_infos_map:
            raise ValueError("host_info_list 和 subscription_id__bk_host_ids_info_map 不能同时为空")
        # 如果 host_info_list 不为空，那么就直接使用 host_info_list 中的主机信息, 并且转换为 subscription_id__bk_host_ids_info_map
        if host_info_list:
            subscription_id__bk_host_infos_map = defaultdict(list)
            if not isinstance(host_info_list, list):
                raise ValueError("host_info_list 必须为列表")
            for host_info in host_info_list:
                if isinstance(host_info, int):
                    subscription_id__bk_host_infos_map["CUSTOM"].append({"bk_host_id": host_info})
                elif isinstance(host_info, str):
                    try:
                        bk_cloud_id, inner_ip = host_info.split(":")
                    except ValueError:
                        raise ValueError(f"host_info_list 中的主机信息 ->  [{host_info}]必须为 cloud_id:ip 的形式")
                    subscription_id__bk_host_infos_map["CUSTOM"].append(
                        {
                            "bk_cloud_id": bk_cloud_id,
                            "ip": inner_ip,
                        }
                    )
        if not isinstance(subscription_id__bk_host_infos_map, dict):
            raise ValueError("subscription_id__bk_host_ids_info_map 必须为字典")

        # 如果 script_content_map 不包括 bat 和 shell 的其中一种，则只查询包括的类型 os_type
        if not script_content_map.get(
            constants.ScriptLanguageType.get_member_value__alias_map()[constants.ScriptLanguageType.BAT.value]
        ):
            host_query = Host.objects.exclude(os_type=constants.OsType.WINDOWS)
        elif not script_content_map.get(
            constants.ScriptLanguageType.get_member_value__alias_map()[constants.ScriptLanguageType.SHELL.value]
        ):
            host_query = Host.objects.filter(os_type=constants.OsType.WINDOWS)
        else:
            host_query = Host.objects.all()

        # 如果是 int 类型，直接追加到列表，如果是 dict 类型，先校验是否有 bk_cloud_id 和 ip，然后根据 ip 和 bk_cloud_id 查出 bk_host_id
        anomaly_status_host_info_map = []
        for subscription_id, bk_host_info_list in subscription_id__bk_host_infos_map.items():
            filtered_bk_host_ids = []
            need_query_host_info_list: List[Dict[str, Union[str, int]]] = []
            # 如果能拿到 bk_host_id  就直接用 bk_host_id, 拿不到就用后面的 ip 和 bk_cloud_id 查出 bk_host_id
            for bk_host_info in bk_host_info_list:
                bk_host_id = bk_host_info.get("bk_host_id")
                if bk_host_id:
                    filtered_bk_host_ids.append(bk_host_id)
                else:
                    need_query_host_info_list.append(bk_host_info)
            host_info_query_objects = [
                Q(inner_ip=host_info.get("ip"), bk_cloud_id=host_info.get("bk_cloud_id"))
                if basic.is_v4(host_info.get("ip"))
                else Q(inner_ipv6=host_info.get("ip"), bk_cloud_id=host_info.get("bk_cloud_id"))
                for host_info in need_query_host_info_list
            ]
            sub_host_ids = (
                list(
                    set(
                        filtered_bk_host_ids
                        + list(host_query.filter(*host_info_query_objects).values_list("bk_host_id", flat=True))
                    )
                )
                if host_info_query_objects
                else list(set(filtered_bk_host_ids))
            )

            # 把所有的主机查出来，根据主机的操作系统分组，windows 的为一组，其他的为一组
            host_objs = host_query.filter(bk_host_id__in=sub_host_ids).values_list("os_type", "bk_host_id")
            sorted_host_objs = sorted(host_objs, key=itemgetter(0))

            # 然后，使用 groupby 函数进行分组
            job_params = {}
            grouped_host_objs = groupby(sorted_host_objs, key=itemgetter(0))
            for os_type, group in grouped_host_objs:
                account_alias = (settings.BACKEND_UNIX_ACCOUNT, settings.BACKEND_WINDOWS_ACCOUNT)[
                    os_type == constants.OsType.WINDOWS
                ]
                script_language = (constants.ScriptLanguageType.SHELL.value, constants.ScriptLanguageType.BAT.value)[
                    os_type == constants.OsType.WINDOWS
                ]
                job_params.update(
                    {
                        "bk_biz_id": settings.BLUEKING_BIZ_ID,
                        "bk_scope_type": constants.BkJobScopeType.BIZ_SET.value,
                        "bk_scope_id": settings.BLUEKING_BIZ_ID,
                        "script_language": script_language,
                        "script_content": base64.b64encode(
                            script_content_map[
                                constants.ScriptLanguageType.get_member_value__alias_map()[script_language]
                            ].encode()
                        ).decode(),
                        "script_param": base64.b64encode(script_param.encode()).decode(),
                        "task_name": f"NODE_MAN_{subscription_id}_{self.__class__.__name__}",
                        "account_alias": account_alias,
                        "target_server": {"host_id_list": [host[1] for host in list(group)]},
                    }
                )
                job_instance_id = JobApi.fast_execute_script(job_params)["job_instance_id"]
                task_result = JobDemand.poll_task_result(job_instance_id)

                task_detail = task_result["task_result"]
                if not task_result["is_finished"]:
                    raise Exception(f"任务执行超时，job_instance_id  -> [{job_instance_id}]")
                if not task_detail["pending"] and not task_detail["failed"]:
                    continue
                # 这里不关注成功的，只关注脚本返回码不为 0 的
                for failed_host in task_detail["failed"]:
                    anomaly_status_host_info_map.append(
                        {
                            "subscription_id": subscription_id,
                            "bk_host_id": failed_host["bk_host_id"],
                            "log_content": failed_host["log_content"],
                            "os_type": os_type,
                        }
                    )

        return anomaly_status_host_info_map
