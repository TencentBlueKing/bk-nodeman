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

from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set, Union

from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.node_man import exceptions, models
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.utils.local import get_request_username
from common.api import NodeApi


class PolicyTools:
    @classmethod
    def get_policy(cls, policy_id: int, show_deleted: bool = False, need_steps: bool = False) -> Dict[str, Any]:
        """
        策略详细
        :param policy_id: 策略ID
        :param show_deleted: 是否展示已删除的策略
        :param need_steps: 是否需要steps信息，该字段需要查DB，如需用到该字段，可传入 need_steps=True
        :return:
        """

        policies = cls.fetch_policies({policy_id}, show_deleted=show_deleted, need_steps=need_steps)
        if len(policies) == 0:
            raise exceptions.PolicyNotExistError(_("不存在ID为: {id} 的策略").format(id=policy_id))

        return policies[0]

    @classmethod
    def fetch_policies(
        cls, policy_ids: Union[List[int], Set[int]], show_deleted: bool = False, need_steps: bool = False
    ) -> List[Dict[str, Any]]:
        """
        批量获取策略
        :param policy_ids: 策略ID列表
        :param show_deleted: 是否展示已删除的策略
        :param need_steps: 是否需要steps信息，该字段需要查DB，如需用到该字段，可传入 need_steps=True
        :return:
        """

        policy_ids = set(policy_ids)
        # 策略属于订阅的一种类型
        select_fields = ["id", "name", "enable", "category", "plugin_name", "bk_biz_scope", "pid"] + [
            # 构造 scope 所需字段
            "bk_biz_id",
            "object_type",
            "node_type",
            "nodes",
        ]

        policies = models.Subscription.objects.filter(
            id__in=policy_ids, category=models.Subscription.CategoryType.POLICY, show_deleted=show_deleted
        ).values(*select_fields)

        # 提前终止，减少无效查询和计算
        if not policies:
            return []

        for policy in policies:
            policy["scope"] = {
                "bk_biz_id": None,
                "object_type": policy.pop("object_type"),
                "node_type": policy.pop("node_type"),
                "nodes": policy.pop("nodes"),
            }

        if not need_steps:
            return policies

        all_steps = models.SubscriptionStep.objects.filter(subscription_id__in=policy_ids).values(
            "subscription_id", "step_id", "type", "config", "params"
        )
        steps_gby_policy_id = defaultdict(list)
        for step in all_steps:
            steps_gby_policy_id[step["subscription_id"]].append(
                {"id": step["step_id"], "type": step["type"], "config": step["config"], "params": step["params"]}
            )

        for policy in policies:
            policy["steps"] = steps_gby_policy_id.get(policy["id"], [])
            cls.simplify_steps(policy_info=policy, settings_key="config", simple_key="configs")
            cls.simplify_steps(policy_info=policy, settings_key="params", simple_key="params")

        return policies

    @staticmethod
    def simplify_steps(policy_info: dict, settings_key: str, simple_key: str):
        if not ("steps" in policy_info and policy_info["steps"]):
            return
        if settings_key in policy_info["steps"][0]:
            if "details" in policy_info["steps"][0][settings_key]:
                # 属于策略的配置列表，把details转为steps下的configs属性
                policy_info["steps"][0][simple_key] = policy_info["steps"][0][settings_key]["details"]
            else:
                # 原先订阅，没有details，把config作为一个元素放进configs
                policy_info["steps"][0][simple_key] = [policy_info["steps"][0][settings_key]]
                # 属性同级同名无需删除
            if settings_key != simple_key:
                policy_info["steps"][0].pop(settings_key, None)

    @staticmethod
    def parse_steps(policy_info: dict, settings_key: str, simple_key: str):
        if not ("steps" in policy_info and policy_info["steps"]):
            return
        if simple_key in policy_info["steps"][0]:
            policy_info["steps"][0][settings_key] = {"details": policy_info["steps"][0][simple_key]}
            # 属性同级同名无需删除
            if settings_key != simple_key:
                policy_info["steps"][0].pop(simple_key, None)

    @staticmethod
    def get_policy_configs(policy_info: Dict) -> List[Dict]:
        """
        获取策略配置
        :param policy_info:
        :return:
        """
        if not (policy_info.get("steps") and policy_info["steps"][0].get("configs")):
            return []
        return policy_info["steps"][0]["configs"]

    @classmethod
    def get_os_cpu__config_map(cls, policy_info: Dict) -> Dict[str, Dict]:
        os_cpu_config_map = {}
        for policy_config in cls.get_policy_configs(policy_info):
            os_cpu_config_map[f"{policy_config['os']}_{policy_config['cpu_arch']}"] = policy_config
        return os_cpu_config_map

    @classmethod
    def create_job(
        cls,
        job_type: str,
        subscription_id: int,
        task_id: int,
        bk_biz_scope: Union[List[int], Set[int]],
    ) -> Dict[str, int]:

        job = models.Job.objects.create(
            job_type=job_type,
            bk_biz_scope=list(bk_biz_scope),
            subscription_id=subscription_id,
            task_id_list=[task_id],
            # 状态统计交由定时任务calculate_statistics，减少无意义的DB内主机查询
            statistics={},
            error_hosts=[],
            created_by=get_request_username(),
        )

        return {"job_id": job.id}

    @classmethod
    def set_policy_enable(cls, policy_ids: List[int], enable: bool) -> int:
        updated_cnt = models.Subscription.objects.filter(id__in=set(policy_ids)).update(
            enable=enable, update_time=timezone.now()
        )
        return updated_cnt

    @classmethod
    def get_policy_id___associated_host_num_map(cls, policy_ids: Union[Set[int], List[int]]) -> Dict[int, int]:
        """获取策略-关联主机（进程）数量的映射关系"""
        policy_ids = set(policy_ids)

        all_str_source_ids = models.ProcessStatus.objects.filter(source_id__in=policy_ids, is_latest=True).values_list(
            "source_id", flat=True
        )

        all_source_ids = [int(str_source_id) for str_source_id in all_str_source_ids]
        policy_id___associated_host_num_map = dict(Counter(all_source_ids))

        # 查询不到关联进程数量默认填充0
        for policy_id in policy_ids:
            if policy_id in policy_id___associated_host_num_map:
                continue
            policy_id___associated_host_num_map[policy_id] = 0

        return policy_id___associated_host_num_map

    @classmethod
    def get_policies_gby_pid(cls, policy_ids: Union[Set[int], List[int]]) -> Dict[int, List[Dict]]:
        """
        获取给定策略ID - 子（灰度）策略列表
        :param policy_ids: 策略ID列表
        :return: 策略ID - 子（灰度）策略列表 映射关系
        """
        child_policies = models.Subscription.objects.filter(pid__in=set(policy_ids)).values(
            "id", "name", "plugin_name", "bk_biz_scope", "update_time", "creator", "enable", "pid"
        )

        policies_gby_pid = defaultdict(list)
        for child_policy in child_policies:
            policies_gby_pid[child_policy["pid"]].append(child_policy)

        return policies_gby_pid

    @classmethod
    def fetch_all_policies_by_policy_list(cls, policy_list: List[Dict]) -> List[Dict]:
        """
        通过给定的策略列表，获取全量策略（主策略 + 各级子策略），不做深拷贝，便于填充数据
        :param policy_list:
        :return:
        """
        stack = [] + policy_list
        all_policies = [] + policy_list
        while stack:
            top_node = stack.pop()
            for child_policy in top_node.get("children", []):
                stack.append(child_policy)
                all_policies.append(child_policy)
        return all_policies

    @classmethod
    def fetch_host_ids_controlled_by_policy(cls, policy_id: int, plugin_name: str) -> List[int]:
        """
        获取策略实际管控的机器
        is_latest = True 标明一台主机归属于id为policy_id的策略
        :param policy_id:
        :param plugin_name:
        :return:
        """
        bk_host_ids = models.ProcessStatus.objects.filter(
            source_id=policy_id, source_type=models.ProcessStatus.SourceType.DEFAULT, is_latest=True, name=plugin_name
        ).values_list("bk_host_id", flat=True)

        return bk_host_ids

    @classmethod
    def get_host_nodes_gby_2th_policy_id(
        cls,
        action: str,
        policy_id: Optional[int] = None,
        policy: Optional[Dict[str, Any]] = None,
    ) -> Dict[int, List[Dict[str, Optional[int]]]]:
        """
        获取给定策略ID管控下主机的次优先级策略ID列表
        次优先级策略是指主机所管控策略停用时，会将管控主机拉起的策略
        :param action: 执行动作
        :param policy_id: 策略ID
        :param policy:
        :return: 次优先级策略ID列表
        """

        if not policy:
            policy = cls.get_policy(policy_id, need_steps=False)
        else:
            policy_id = policy["id"]

        host_ids_controlled_by_policy = cls.fetch_host_ids_controlled_by_policy(
            policy_id=policy_id, plugin_name=policy["plugin_name"]
        )
        host_infos = models.Host.objects.filter(bk_host_id__in=host_ids_controlled_by_policy).values(
            "bk_biz_id", "bk_cloud_id", "bk_host_id", "inner_ip"
        )
        host_id__bk_obj_sub_map = models.Subscription.get_host_id__bk_obj_sub_map(
            host_ids_controlled_by_policy, policy["plugin_name"], is_latest=False
        )
        topo_order = CmdbHandler.get_topo_order()
        subscription = models.Subscription.get_subscription(policy_id)

        host_nodes_gby_2th_policy_id = defaultdict(list)
        for host in host_infos:

            # 适配同值但不同数据源的主机信息，DB中host的内网IP字段为 inner_ip，需要适配为 cmdb 返回的字段名称 -> bk_host_innerip
            host["bk_host_innerip"] = host["inner_ip"]
            check_is_suppressed_result = subscription.check_is_suppressed(
                action=action,
                cmdb_host_info=host,
                topo_order=topo_order,
                host_id__bk_obj_sub_map=host_id__bk_obj_sub_map,
            )

            if check_is_suppressed_result["is_suppressed"]:
                host_nodes_gby_2th_policy_id[check_is_suppressed_result["suppressed_by"]["subscription_id"]].append(
                    {"bk_host_id": host["bk_host_id"], "bk_biz_id": host["bk_biz_id"]}
                )
            else:
                ordered_bk_obj_subs = check_is_suppressed_result["ordered_bk_obj_subs"]
                if len(ordered_bk_obj_subs) <= 1:
                    continue
                second_priority_target = ordered_bk_obj_subs[-2]
                second_priority_sub: models.Subscription = second_priority_target["subscription"]
                host_nodes_gby_2th_policy_id[second_priority_sub.id].append(
                    {"bk_host_id": host["bk_host_id"], "bk_biz_id": host["bk_biz_id"]}
                )

        return host_nodes_gby_2th_policy_id

    @classmethod
    def run_sub_task(
        cls, policy_id: int, bk_biz_scope: List[int], scope: Dict[str, Any], actions: Dict[str, str], job_type: str
    ) -> Dict[str, Any]:
        """
        执行任务
        :param policy_id: 策略ID
        :param bk_biz_scope:
        :param scope: 执行范围
        :param actions: 执行动作
        :param job_type: 任务类型
        :return:
        """
        run_subscription_task_result = NodeApi.run_subscription_task(
            {"subscription_id": policy_id, "scope": scope, "actions": actions}
        )

        run_subscription_task_result.update(
            cls.create_job(
                job_type=job_type,
                subscription_id=run_subscription_task_result["subscription_id"],
                task_id=run_subscription_task_result["task_id"],
                bk_biz_scope=bk_biz_scope,
            )
        )

        return run_subscription_task_result
