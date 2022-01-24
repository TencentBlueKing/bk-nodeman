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

import operator
from collections import ChainMap, Counter, defaultdict
from copy import deepcopy
from functools import reduce
from itertools import chain, groupby
from typing import Any, Dict, List, Optional, Set, Union

from django.conf import settings
from django.db.models import Max, Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from packaging import version

from apps.backend.constants import PluginMigrateType
from apps.backend.subscription import tasks
from apps.backend.subscription.constants import MAX_RETRY_TIME
from apps.node_man import constants, exceptions, models, tools
from apps.node_man.constants import IamActionType
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host_v2 import HostV2Handler
from apps.node_man.handlers.iam import IamHandler
from apps.utils import concurrent
from apps.utils.basic import distinct_dict_list
from apps.utils.local import get_request_username
from common.api import NodeApi


class PolicyHandler:
    @staticmethod
    def policy_info(policy_id: int) -> Dict[str, Any]:
        """
        策略详细
        :param policy_id: 策略ID
        :return:
        """
        policy_info = tools.PolicyTools.get_policy(policy_id, need_steps=True)

        # 兼容原有订阅任务，如果不是策略类型订阅无需返回插件信息
        if policy_info["category"] != constants.SubscriptionType.POLICY:
            return policy_info

        plugin_desc_obj = models.GsePluginDesc.objects.get(name=policy_info["plugin_name"])
        policy_info.update(
            {
                "plugin_info": {
                    "id": plugin_desc_obj.id,
                    "name": plugin_desc_obj.name,
                    "description": plugin_desc_obj.description,
                    "source_app_code": plugin_desc_obj.source_app_code,
                    "category": constants.CATEGORY_DICT[plugin_desc_obj.category],
                    "deploy_type": constants.DEPLOY_TYPE_DICT[plugin_desc_obj.deploy_type]
                    if plugin_desc_obj.deploy_type
                    else plugin_desc_obj.deploy_type,
                },
            }
        )
        return policy_info

    @staticmethod
    def update_policy_info(username: str, policy_id: int, update_data: Dict[str, Any]) -> None:
        """
        更新策略概要信息
        :param username: 操作人
        :param policy_id: 策略id
        :param update_data: 更新数据
        :return:
        """
        policy = models.Subscription.objects.filter(id=policy_id).first()
        if policy is None:
            raise exceptions.PolicyNotExistError(_("不存在ID为: {id} 的策略").format(id=policy_id))
        policy.creator = username
        policy.name = update_data["name"]
        policy.save(update_fields=["creator", "name", "update_time"])

    @staticmethod
    def search_deploy_policy(query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        查询策略
        :param query_params: 查询参数
        :return: 策略列表
        """

        strategy_operate_perm = []

        is_superuser = IamHandler().is_superuser(get_request_username())

        if not is_superuser:
            user_biz = CmdbHandler().biz_id_name({"action": IamActionType.strategy_view}, get_request_username())

            if settings.USE_IAM:
                perms = IamHandler().fetch_policy(
                    get_request_username(),
                    [constants.IamActionType.strategy_operate],
                )
                strategy_operate_perm = perms["strategy_operate"]

            query_biz = query_params.get("bk_biz_ids", [])
            if query_biz:
                query_params["bk_biz_ids"] = list(set(user_biz.keys()) & set(query_biz))
            else:
                query_params["bk_biz_ids"] = list(user_biz.keys())

            if not query_params["bk_biz_ids"]:
                # 业务为空直接返回
                return {"total": 0, "list": []}

        root_policy_page = NodeApi.subscription_search_policy(query_params)

        # 默认收起灰度，only_root=False时展开显示，适配前端轮训获取job状态
        if query_params["only_root"]:
            root_policy_id_list = [policy["id"] for policy in root_policy_page["list"]]
            policies_gby_pid = tools.PolicyTools.get_policies_gby_pid(root_policy_id_list)
        else:
            policies_gby_pid = {}

        for root_policy in root_policy_page["list"]:
            root_policy["children"] = policies_gby_pid.get(root_policy["id"], [])

        all_policies = tools.PolicyTools.fetch_all_policies_by_policy_list(root_policy_page["list"])
        all_policy_ids = [policy["id"] for policy in all_policies]

        # 查询每个策略下最新的任务
        latest_task_ids_in_same_policy = (
            models.SubscriptionTask.objects.filter(subscription_id__in=all_policy_ids)
            .values("subscription_id")
            .annotate(id=Max("id"))
            .values_list("id", flat=True)
        )
        sub_tasks = models.SubscriptionTask.objects.filter(id__in=latest_task_ids_in_same_policy).values(
            "id", "subscription_id", "is_ready", "err_msg", "is_auto_trigger"
        )
        job_objs = tools.JobTools.list_sub_task_related_jobs(
            subscription_ids=all_policy_ids, task_ids=[task["id"] for task in sub_tasks]
        )
        sub_id__task_map = {task["subscription_id"]: task for task in sub_tasks}
        sub_id__job_obj_map: Dict[int, models.Job] = {job_obj.subscription_id: job_obj for job_obj in job_objs}

        # 业务ID - 业务名称映射
        biz_id__biz_name_map = CmdbHandler.biz_id_name_without_permission()

        # 获取插件名称 - 插件ID映射关系
        plugin_name__plugin_id_map = {
            plugin_info["name"]: plugin_info["id"]
            for plugin_info in models.GsePluginDesc.objects.filter(
                name__in={policy["plugin_name"] for policy in all_policies}
            ).values("id", "name")
        }

        # 查询策略ID - 已部署节点映射关系
        policy_id___associated_host_num_map = tools.PolicyTools.get_policy_id___associated_host_num_map(all_policy_ids)

        # 计算策略ID - 策略详情映射关系
        id__policy_detail_map = {
            policy_detail["id"]: policy_detail
            for policy_detail in tools.PolicyTools.fetch_policies(all_policy_ids, need_steps=True)
        }

        # 获取系统类型 - 最新插件包可用版本映射
        proj_os_cpu__latest_version_map = tools.PluginV2Tools.get_proj_os_cpu__latest_version_map(
            projects=[policy["plugin_name"] for policy in all_policies]
        )

        # 填充各级策略都需要的通用字段
        for policy in all_policies:
            policy["configs"] = []
            policy["need_to_upgrade"] = False
            policy_detail = id__policy_detail_map.get(policy["id"], {})
            for config in tools.PolicyTools.get_policy_configs(policy_detail):
                policy["configs"].append(
                    {"os": config["os"], "cpu_arch": config["cpu_arch"], "version": config["version"]}
                )
                proj_os_cpu_key = f"{policy['plugin_name']}_{config['os']}_{config['cpu_arch']}"
                if not proj_os_cpu__latest_version_map.get(proj_os_cpu_key):
                    continue
                # 是否升级已更新为True，无须再进行版本对比
                if policy["need_to_upgrade"]:
                    continue
                if version.parse(proj_os_cpu__latest_version_map[proj_os_cpu_key]) > version.parse(config["version"]):
                    policy["need_to_upgrade"] = True

            # 填充插件ID
            policy["plugin_id"] = plugin_name__plugin_id_map.get(policy["plugin_name"])

            # 填充业务名称
            bk_biz_scope = [
                {"bk_biz_id": bk_biz_id, "bk_biz_name": biz_id__biz_name_map.get(bk_biz_id)}
                for bk_biz_id in policy["bk_biz_scope"]
            ]
            policy["bk_biz_scope"] = bk_biz_scope

            # TODO 权限中心适配，灰度策略是依附父策略还是独立
            if not is_superuser and settings.USE_IAM:
                has_permission = (
                    policy["pid"] in strategy_operate_perm
                    if policy.get("pid", -1) != -1
                    else policy["id"] in strategy_operate_perm
                )
            else:
                has_permission = True
            policy["permissions"] = {"edit": has_permission}

            # 填充任务执行状态
            policy["job_result"] = {}
            if policy["id"] in sub_id__job_obj_map:
                task, job_obj = sub_id__task_map[policy["id"]], sub_id__job_obj_map[policy["id"]]
                policy["job_result"]["task"] = task
                policy["job_result"].update(
                    {
                        "job_id": job_obj.id,
                        "is_auto_trigger": job_obj.is_auto_trigger,
                        # TODO 错误发生在subscription_task创建过程中，此时job的状态应为失败，考虑后续该状态反写到Job
                        "status": constants.JobStatusType.FAILED if task["err_msg"] else job_obj.status,
                        **tools.JobTools.unzip_job_type(job_obj.job_type),
                    }
                )

            # 填充关联主机数
            policy["associated_host_num"] = policy_id___associated_host_num_map.get(policy["id"])

        # 灰度策略与父策略的版本比较
        for root_policy in root_policy_page["list"]:
            os_cpu__version_map = {
                f"{config['os']}_{config['cpu_arch']}": config["version"] for config in root_policy["configs"]
            }
            child_configs = list(
                chain(*[child_policy.get("configs", []) for child_policy in root_policy.get("children", [])])
            )
            for child_config in child_configs:
                root_version = os_cpu__version_map.get(f"{child_config['os']}_{child_config['cpu_arch']}")
                if not root_version or version.parse(root_version) < version.parse(child_config["version"]):
                    child_config["compare_with_root"] = 1
                elif version.parse(root_version) > version.parse(child_config["version"]):
                    child_config["compare_with_root"] = -1
                else:
                    child_config["compare_with_root"] = 0

        return root_policy_page

    @staticmethod
    def fetch_policy_topo(
        bk_biz_ids: Optional[List[int]] = None,
        plugin_name: Optional[str] = None,
        keyword: Optional[str] = None,
        is_lazy: bool = False,
    ) -> List[Dict]:
        """
        拉取策略拓扑
        :return: 策略拓扑
        """
        # 没有指定业务id列表时取用户有权限的全部业务
        user_biz_ids = set(CmdbHandler().biz_id_name({"action": constants.IamActionType.strategy_view}).keys())
        if bk_biz_ids is not None:
            bk_biz_ids = set(bk_biz_ids) & user_biz_ids
        else:
            bk_biz_ids = user_biz_ids

        if not bk_biz_ids:
            return []

        # 构造业务ID筛选逻辑，筛选出 策略业务范围 与 搜索业务范围 有交集的策略，contains仅支持单值包含筛选，需要Q通过逻辑或的方式进行查找
        biz_query = reduce(operator.or_, [Q(bk_biz_scope__contains=bk_biz_id) for bk_biz_id in bk_biz_ids], Q())
        policy_qs = models.Subscription.objects.filter(Q(category=models.Subscription.CategoryType.POLICY), biz_query)

        if plugin_name:
            policy_qs = policy_qs.filter(plugin_name=plugin_name)
        if keyword is not None:
            filter_fields = ["plugin_name", "name"]
            kw_query = reduce(
                operator.or_, [Q(**{f"{filter_field}__contains": keyword}) for filter_field in filter_fields], Q()
            )
            policy_qs = policy_qs.filter(kw_query)

        # 懒加载模式下仅展示一级节点（插件）
        if is_lazy:
            plugin_names = set(policy_qs.values_list("plugin_name", flat=True))
            return [
                {"id": plugin_name, "name": plugin_name, "type": "plugin", "children": []}
                for plugin_name in plugin_names
            ]

        # 按插件名称聚合构造的策略节点
        policy_nodes_gby_plugin_name = defaultdict(list)
        policy_infos = policy_qs.values("id", "name", "category", "plugin_name")
        for policy_info in policy_infos:
            policy_nodes_gby_plugin_name[policy_info["plugin_name"]].append(
                {"id": policy_info["id"], "name": policy_info["name"], "type": policy_info["category"]}
            )

        # 构造策略拓扑
        policy_topo = []
        for _plugin_name, policy_nodes in policy_nodes_gby_plugin_name.items():
            policy_topo.append({"id": _plugin_name, "name": _plugin_name, "type": "plugin", "children": policy_nodes})
        return policy_topo

    @staticmethod
    def selected_preview(query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        策略预览
        :param query_params: 创建策略参数及搜索条件
        :return: 安装目标主机列表
        """
        result = {}
        if "policy_id" in query_params:
            # 预览涉及更新场景，优先使用接口传入的修改参数
            query_params = dict(
                ChainMap(query_params, tools.PolicyTools.get_policy(query_params["policy_id"], need_steps=True))
            )

        if not query_params["with_hosts"]:
            return result
        result.update(
            HostV2Handler.list(
                params=query_params,
                with_agent_status_counter=True,
                view_action=constants.IamActionType.strategy_create,
                op_action=constants.IamActionType.strategy_create,
                return_all_node_type=True,
            )
        )

        os_cpu__config_map = tools.PolicyTools.get_os_cpu__config_map(query_params)
        bk_host_id_plugin_version_map = tools.HostV2Tools.get_bk_host_id_plugin_version_map(
            bk_host_ids=[host_info["bk_host_id"] for host_info in result["list"]],
            project=query_params["steps"][0]["id"],
        )

        # 匹配插件版本
        for host_info in result["list"]:
            os_cpu_key = f"{host_info['os_type'].lower()}_{host_info['cpu_arch']}"

            host_info["current_version"] = bk_host_id_plugin_version_map.get(host_info["bk_host_id"])
            host_info["target_version"] = os_cpu__config_map.get(os_cpu_key, {}).get("version")

        return result

    @staticmethod
    def migrate_preview(query_params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """变更计算预览"""

        scope = query_params["scope"]
        try:
            subscription = models.Subscription.objects.get(id=query_params.get("policy_id"), is_deleted=False)
        except models.Subscription.DoesNotExist:
            subscription = models.Subscription(
                bk_biz_id=scope.get("bk_biz_id"),
                object_type=scope["object_type"],
                node_type=scope["node_type"],
                nodes=scope["nodes"],
                target_hosts=query_params.get("target_hosts"),
                # SaaS侧均为主程序部署
                is_main=True,
                category=query_params["category"],
                create_time=timezone.now(),
            )
        else:
            subscription.node_type = scope["node_type"]
            subscription.nodes = scope["nodes"]
            subscription.bk_biz_id = scope.get("bk_biz_id")

        subscription_task = models.SubscriptionTask(
            subscription_id=subscription.id, scope=subscription.scope, actions={}
        )

        # None 表示策略部署，一次性操作需要指定job_type用于豁免make_instances_migrate_actions
        job_type: Union[str, None] = query_params.get("job_type")
        # SaaS侧手动操作的安装也使用新接口协议，需要转化
        if subscription.category == models.Subscription.CategoryType.POLICY or job_type in [
            constants.JobType.MAIN_INSTALL_PLUGIN
        ]:
            tools.PolicyTools.parse_steps(query_params, settings_key="config", simple_key="configs")
            tools.PolicyTools.parse_steps(query_params, settings_key="params", simple_key="params")

        # 如果指定job_type并且job_type非安装，需要重新构造steps用于变更对比
        if job_type not in [None, constants.JobType.MAIN_INSTALL_PLUGIN]:
            if subscription.category == models.Subscription.CategoryType.POLICY:
                plugin_name = subscription.plugin_name
            else:
                plugin_name = query_params["plugin_name"]

            config_templates = models.PluginConfigTemplate.objects.filter(plugin_name=plugin_name, is_main=True)
            query_params["steps"] = [
                {
                    "config": {
                        "config_templates": distinct_dict_list(
                            [
                                {"name": conf_tmpl.name, "version": "latest", "is_main": True}
                                for conf_tmpl in config_templates
                            ]
                        ),
                        "plugin_name": plugin_name,
                        "plugin_version": "latest",
                        "job_type": job_type,
                    },
                    "type": "PLUGIN",
                    "id": plugin_name,
                    "params": {},
                }
            ]

        steps = []
        for index, step in enumerate(query_params["steps"]):
            step = models.SubscriptionStep(
                # 如果是未创建的订阅，提供假id用于减少sql扫描范围，由于ProcessStatus source_id为None时数据量大，不建议用None
                subscription_id=subscription.id or -1,
                index=index,
                step_id=step["id"],
                type=step["type"],
                config=step["config"],
                params=step["params"],
            )
            steps.append(step)
            step.subscription = subscription
        subscription.steps = steps
        preview_result = tasks.run_subscription_task_and_create_instance(
            subscription, subscription_task, preview_only=True
        )
        action_instance_map = defaultdict(list)
        instance_actions = preview_result["instance_actions"]
        instance_migrate_reasons = preview_result["instance_migrate_reasons"]
        instance_id__inst_info_map = preview_result["instance_id__inst_info_map"]
        for instance_id, instance_record in preview_result["to_be_created_records_map"].items():
            host_info = instance_record.instance_info["host"]
            for step_id, action_id in instance_actions.get(instance_id, {}).items():
                try:
                    migrate_reason = instance_migrate_reasons[instance_id][step_id]
                except KeyError:
                    migrate_reason = {}
                action_instance_map[action_id].append(
                    {**tools.HostV2Tools.retrieve_host_info(host_info), "migrate_reason": migrate_reason}
                )
        if preview_result.get("error_hosts"):
            action_instance_map[constants.OpType.IGNORED] = preview_result["error_hosts"]

        # 补充无需变更主机
        for instance_id, step_id__migrate_reason_map in instance_migrate_reasons.items():
            host_info = instance_id__inst_info_map.get(instance_id, {}).get("host", {})
            for step in query_params["steps"]:
                step_id = step["id"]
                if step_id not in step_id__migrate_reason_map:
                    continue
                if step_id__migrate_reason_map[step_id].get("migrate_type") != PluginMigrateType.NOT_CHANGE:
                    continue
                action_instance_map[PluginMigrateType.NOT_CHANGE].append(
                    {
                        **tools.HostV2Tools.retrieve_host_info(host_info),
                        "migrate_reason": step_id__migrate_reason_map[step_id],
                    }
                )

        # 补充业务名、云区域名称
        cloud_id_name_map = models.Cloud.cloud_id_name_map()
        biz_name_map = CmdbHandler.biz_id_name_without_permission()

        results = []
        for action_id, instances in action_instance_map.items():
            for instance in instances:
                instance.update(
                    bk_biz_name=biz_name_map.get(instance.get("bk_biz_id")),
                    bk_cloud_name=cloud_id_name_map.get(instance["bk_cloud_id"]),
                )

            inst_job_type = constants.ACTION_NAME_JOB_TYPE_MAP.get(action_id)
            op_type = tools.JobTools.unzip_job_type(inst_job_type)["op_type"] if inst_job_type else action_id

            migrate_result = {
                "action_id": action_id,
                "action_name": constants.OP_TYPE_ALIAS_MAP.get(op_type, op_type),
                "list": instances,
            }
            # 一次性订阅策略抑制文案显示为 - 策略管控
            if action_id == constants.OpType.IGNORED and subscription.category == models.Subscription.CategoryType.ONCE:
                migrate_result["action_name"] = constants.OP_TYPE_ALIAS_MAP[constants.OpType.POLICY_CONTROL]

            if action_id in PluginMigrateType.MIGRATE_TYPES:
                migrate_result["action_name"] = PluginMigrateType.MIGRATE_TYPE_ALIAS_MAP[action_id]

            results.append(migrate_result)
        return results

    @classmethod
    def create_deploy_policy(cls, create_data: dict) -> Dict[str, int]:
        """
        创建策略
        :param create_data: 创建参数
        :return: {"subscription_id": 1}
        """
        bk_biz_scope = list(set([node["bk_biz_id"] for node in create_data["scope"]["nodes"]]))

        create_data.update(
            {
                "plugin_name": create_data["steps"][0]["id"],
                "bk_biz_scope": bk_biz_scope,
                "category": constants.SubscriptionType.POLICY,
                "is_main": True,  # 目前仅支持主程序部署策略，子配置部署策略在后台提供能力，由第三方系统调用实现
                "run_immediately": True,
            }
        )
        tools.PolicyTools.parse_steps(create_data, settings_key="config", simple_key="configs")
        tools.PolicyTools.parse_steps(create_data, settings_key="params", simple_key="params")

        create_result = NodeApi.create_subscription(create_data)

        create_result.update(
            tools.PolicyTools.create_job(
                job_type=constants.JobType.MAIN_INSTALL_PLUGIN,
                subscription_id=create_result["subscription_id"],
                task_id=create_result["task_id"],
                bk_biz_scope=create_data["bk_biz_scope"],
            )
        )

        # 灰度策略不需要创建关联权限 # todo 创建需要传pid
        if create_data.get("pid", -1) == -1 and settings.USE_IAM:
            # 将创建者返回权限中心
            ok, message = IamHandler.return_resource_instance_creator(
                "strategy", create_result["subscription_id"], create_data["name"], get_request_username()
            )
            if not ok:
                raise PermissionError(_("权限中心创建关联权限失败: {}".format(message)))

        return create_result

    @classmethod
    def update_policy(cls, update_data: Dict[str, Any], policy_id: int) -> Dict[str, Any]:
        """
        更新策略
        :param update_data: 更新数据
        :param policy_id: 策略ID
        :return: {"subscription_id": 1}
        """

        tools.PolicyTools.parse_steps(update_data, settings_key="config", simple_key="configs")
        tools.PolicyTools.parse_steps(update_data, settings_key="params", simple_key="params")

        update_data.update(
            {
                "subscription_id": policy_id,
                "plugin_name": update_data["steps"][0]["id"],
                "bk_biz_scope": list(set([node["bk_biz_id"] for node in update_data["scope"]["nodes"]])),
                "run_immediately": True,
            }
        )
        update_result = NodeApi.subscription_update(update_data)

        update_result.update(
            tools.PolicyTools.create_job(
                job_type=constants.JobType.MAIN_INSTALL_PLUGIN,
                subscription_id=update_result["subscription_id"],
                task_id=update_result["task_id"],
                bk_biz_scope=update_data["bk_biz_scope"],
            )
        )
        return update_result

    @staticmethod
    def upgrade_preview(policy_id: int) -> List[Dict[str, Any]]:
        """
        升级预览
        :param policy_id:
        :return:
        """

        policy_info = PolicyHandler.policy_info(policy_id)
        plugin_info = NodeApi.plugin_retrieve({"plugin_id": policy_info["plugin_info"]["id"]})

        # 拉取最新版本的包
        os_cpu_latest_pkg_map = {}
        for pkg in plugin_info.get("plugin_packages", []):
            os_cpu_latest_pkg_map[f"{pkg['os']}_{pkg['cpu_arch']}"] = pkg

        host_infos = tools.HostV2Tools.list_scope_hosts(policy_info["scope"])
        host_infos = sorted(host_infos, key=lambda x: (x["os"], x["cpu_arch"]))

        bk_host_id_plugin_version_map = tools.HostV2Tools.get_bk_host_id_plugin_version_map(
            project=policy_info["plugin_info"]["name"],
            bk_host_ids=[host_info["bk_host_id"] for host_info in host_infos],
        )

        version_count_group_by_os_cpu = {}
        for os_cpu, hosts_part in groupby(host_infos, key=lambda x: f"{x['os']}_{x['cpu_arch']}"):
            # TODO 后续需要考虑静态主机移除的情况
            version_count_group_by_os_cpu[os_cpu] = dict(
                Counter([bk_host_id_plugin_version_map.get(host_info["bk_host_id"]) for host_info in list(hosts_part)])
            )

        upgrade_info_list = []
        for policy_config in tools.PolicyTools.get_policy_configs(policy_info):
            base_info = {"cpu_arch": policy_config["cpu_arch"], "os": policy_config["os"]}
            os_cpu_key = f"{policy_config['os']}_{policy_config['cpu_arch']}"
            upgrade_info = {
                **base_info,
                "latest_version": os_cpu_latest_pkg_map[os_cpu_key]["version"],
                "current_version_list": [],
            }

            # 考虑已部署插件被删除 / 都被停用的情况
            if os_cpu_key not in os_cpu_latest_pkg_map or not os_cpu_latest_pkg_map[os_cpu_key]["is_ready"]:
                upgrade_info["current_version_list"] = [
                    {**base_info, "current_version": current_version, "nodes_number": nodes_number}
                    for current_version, nodes_number in version_count_group_by_os_cpu.get(os_cpu_key, {}).items()
                ]
                upgrade_info["is_latest"] = True
                upgrade_info_list.append(upgrade_info)
                continue

            def get_upgrade_info(is_latest: bool):
                version_counter = {
                    current_version: nodes_number
                    for current_version, nodes_number in version_count_group_by_os_cpu.get(
                        os_cpu_key, {policy_config["version"]: 0}
                    ).items()
                    if (
                        version.parse(str(current_version))
                        >= version.parse(str(os_cpu_latest_pkg_map[os_cpu_key]["version"]))
                    )
                    == is_latest
                }
                _upgrade_info = deepcopy(upgrade_info)
                _upgrade_info.update(
                    {
                        "is_latest": is_latest,
                        "current_version_list": [
                            {**base_info, "current_version": current_version, "nodes_number": nodes_number}
                            for current_version, nodes_number in version_counter.items()
                        ],
                    }
                )
                return _upgrade_info

            # 过滤最新版本
            upgrade_info_list.append(get_upgrade_info(True))

            not_latest_upgrade_info = get_upgrade_info(False)
            not_latest_upgrade_info["latest_version"] = os_cpu_latest_pkg_map[os_cpu_key]["version"]
            # TODO 缺少版本描述
            not_latest_upgrade_info["version_scenario"] = _(
                "{plugin_name}: {plugin_description} - V{version} \n 该版本支持{plugin_scenario}"
            ).format(
                plugin_name=plugin_info["name"],
                plugin_description=plugin_info["description"],
                version=os_cpu_latest_pkg_map[os_cpu_key]["version"],
                plugin_scenario=plugin_info["scenario"],
            )
            upgrade_info_list.append(not_latest_upgrade_info)

        return [upgrade_info for upgrade_info in upgrade_info_list if upgrade_info["current_version_list"]]

    @staticmethod
    def plugin_preselection(plugin_id: int, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        :param plugin_id:
        :param scope:
        :return:
        """
        host_infos = tools.HostV2Tools.list_scope_hosts(scope)
        plugin_info = NodeApi.plugin_retrieve({"plugin_id": plugin_id})

        os_cpu_list = {
            f"{host_info['os']}_{host_info['cpu_arch']}"
            for host_info in host_infos
            if host_info["cpu_arch"] in constants.CPU_TUPLE and host_info["os"] in constants.PLUGIN_OS_TUPLE
        }

        for pkg in plugin_info.get("plugin_packages", []):
            pkg["is_preselection"] = f"{pkg['os']}_{pkg['cpu_arch']}" in os_cpu_list

        return plugin_info

    @staticmethod
    def policy_operate(policy_id: int, op_type: str, only_disable: bool = False) -> Dict[str, Any]:
        policy = tools.PolicyTools.get_policy(policy_id, need_steps=False)

        # 删除无需调用后台，直接软删除并返回
        if op_type == constants.PolicyOpType.DELETE:
            operate_result = {}

            # 如果是灰度策略，删除前需要触发管控范围内的次优先级策略重新部署
            if policy["pid"] != models.Subscription.ROOT:
                run_sub_task_results = []
                # 灰度的删除实际是次优先级策略的并发安装
                action = constants.JobType.MAIN_INSTALL_PLUGIN
                host_nodes_gby_2th_policy_id = tools.PolicyTools.get_host_nodes_gby_2th_policy_id(
                    action=action, policy=policy
                )

                # 待删除灰度切换为停用状态，避免影响次优先级策略拉起
                models.Subscription.objects.filter(id=policy_id).update(enable=False)

                for second_policy_id, host_nodes in host_nodes_gby_2th_policy_id.items():
                    scope = {
                        "node_type": models.Subscription.NodeType.INSTANCE,
                        "object_type": models.Subscription.ObjectType.HOST,
                        "nodes": host_nodes,
                    }
                    run_sub_task_result = tools.PolicyTools.run_sub_task(
                        policy_id=second_policy_id,
                        bk_biz_scope=policy["bk_biz_scope"],
                        scope=scope,
                        actions={policy["plugin_name"]: action},
                        job_type=constants.JobType.MAIN_INSTALL_PLUGIN,
                    )
                    run_sub_task_results.append(run_sub_task_result)

                operate_result["operate_results"] = run_sub_task_results

            # 设置enable=False, 兼容强制删除的场景
            delete_num = models.Subscription.objects.filter(id=policy_id).delete(enable=False)
            operate_result["deleted"] = delete_num == 1

            return operate_result

        policy_op_type__job_type_map = {
            constants.PolicyOpType.STOP: constants.JobType.MAIN_STOP_PLUGIN,
            constants.PolicyOpType.START: constants.JobType.MAIN_START_PLUGIN,
            constants.PolicyOpType.RETRY_ABNORMAL: constants.JobType.MAIN_INSTALL_PLUGIN,
            constants.PolicyOpType.STOP_AND_DELETE: constants.JobType.MAIN_STOP_AND_DELETE_PLUGIN,
        }

        if op_type in [constants.PolicyOpType.START]:
            scope = policy["scope"]
        elif op_type == constants.PolicyOpType.STOP and only_disable:
            # 仅停用策略
            return {"updated": tools.PolicyTools.set_policy_enable(policy_ids=[policy_id], enable=False) == 1}
        else:
            if op_type == constants.PolicyOpType.RETRY_ABNORMAL:
                scope_host_ids = tools.HostV2Tools.list_scope_host_ids(policy["scope"])
                abnormal_host_ids = models.ProcessStatus.objects.filter(
                    source_id=policy["id"], retry_times__gt=MAX_RETRY_TIME, bk_host_id__in=scope_host_ids
                ).values_list("bk_host_id", flat=True)
                # ProcessStatus可能存在脏数据，利用策略部署范围过滤掉不在范围内的主机ID
                bk_host_ids = set(scope_host_ids) & set(abnormal_host_ids)
            else:
                # STOP / STOP_AND_DELETE场景下，选择实际部署节点作为操作范围
                bk_host_ids = tools.PolicyTools.fetch_host_ids_controlled_by_policy(
                    policy_id=policy_id, plugin_name=policy["plugin_name"]
                )

            host_nodes = list(models.Host.objects.filter(bk_host_id__in=bk_host_ids).values("bk_host_id", "bk_biz_id"))
            scope = {
                "node_type": models.Subscription.NodeType.INSTANCE,
                "object_type": models.Subscription.ObjectType.HOST,
                "nodes": host_nodes,
            }

        run_sub_task_result = tools.PolicyTools.run_sub_task(
            policy_id=policy_id,
            bk_biz_scope=policy["bk_biz_scope"],
            scope=scope,
            actions={policy["plugin_name"]: policy_op_type__job_type_map[op_type]},
            job_type=policy_op_type__job_type_map[op_type],
        )

        if op_type in [constants.PolicyOpType.STOP]:
            tools.PolicyTools.set_policy_enable(policy_ids=[policy_id], enable=False)

        return run_sub_task_result

    @staticmethod
    def rollback_preview(policy_id: int, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        策略回滚预览 - 移除该策略后管控主机策略归属情况
        :param policy_id:
        :param query_params:
        :return:
        """
        policy = tools.PolicyTools.get_policy(policy_id, need_steps=False)

        host_ids_controlled_by_policy = tools.PolicyTools.fetch_host_ids_controlled_by_policy(
            policy_id=policy_id, plugin_name=policy["plugin_name"]
        )

        query_params["bk_host_id"] = host_ids_controlled_by_policy

        host_page = HostV2Handler.list(
            params=query_params,
            view_action=constants.IamActionType.strategy_operate,
            op_action=constants.IamActionType.strategy_operate,
            return_all_node_type=True,
        )

        topo_order = CmdbHandler.get_topo_order()
        subscription = models.Subscription.get_subscription(policy_id)
        bk_host_ids = {host["bk_host_id"] for host in host_page["list"]}
        host_id__bk_obj_sub_map = models.Subscription.get_host_id__bk_obj_sub_map(
            bk_host_ids, policy["plugin_name"], is_latest=False
        )

        for host in host_page["list"]:

            # 适配同值但不同数据源的主机信息，DB中host的内网IP字段为 inner_ip，需要适配为 cmdb 返回的字段名称 -> bk_host_innerip
            host["bk_host_innerip"] = host["inner_ip"]

            check_is_suppressed_result = subscription.check_is_suppressed(
                # 策略回滚操作的动作为MAIN_INSTALL_PLUGIN
                action=constants.JobType.MAIN_INSTALL_PLUGIN,
                cmdb_host_info=host,
                topo_order=topo_order,
                host_id__bk_obj_sub_map=host_id__bk_obj_sub_map,
            )

            host["target_policy"] = {}
            # 管控主机被其他策略抑制，一般不会出现这种情况
            if check_is_suppressed_result["is_suppressed"]:
                host["target_policy"] = {
                    "id": check_is_suppressed_result["suppressed_by"]["subscription_id"],
                    "name": check_is_suppressed_result["suppressed_by"]["name"],
                    "bk_obj_id": check_is_suppressed_result["suppressed_by"]["bk_obj_id"],
                    "type": constants.PolicyRollBackType.SUPPRESSED,
                }
            else:
                ordered_bk_obj_subs = check_is_suppressed_result["ordered_bk_obj_subs"]
                # 长度1表示当前主机仅被一个策略覆盖，若该策略回滚，该主机将失去管控
                if len(ordered_bk_obj_subs) <= 1:
                    host["target_policy"] = {"type": constants.PolicyRollBackType.LOSE_CONTROL}
                else:
                    second_priority_target = ordered_bk_obj_subs[-2]
                    second_priority_sub: models.Subscription = second_priority_target["subscription"]
                    host["target_policy"] = {
                        "id": second_priority_sub.id,
                        "name": second_priority_sub.name,
                        "bk_obj_id": second_priority_target["bk_obj_id"],
                        "type": constants.PolicyRollBackType.TRANSFER_TO_ANOTHER,
                    }
            host["target_policy"]["msg"] = constants.PolicyRollBackType.ROLLBACK_TYPE__ALIAS_MAP.get(
                host["target_policy"]["type"]
            )

        return host_page

    @staticmethod
    def fetch_policy_abnormal_info(policy_ids: List[int]) -> Dict[int, Any]:
        def _get_policy_scope_info(scope: Dict[str, Any]) -> Dict[str, Any]:
            return {"policy_id": scope["policy_id"], "bk_host_ids": tools.HostV2Tools.list_scope_host_ids(scope)}

        list_scope_host_ids_params_list = []
        policies = tools.PolicyTools.fetch_policies(policy_ids)

        for policy in policies:
            list_scope_host_ids_params_list.append({"scope": {**policy["scope"], "policy_id": policy["id"]}})

        policy_scope_infos = concurrent.batch_call(
            func=_get_policy_scope_info, params_list=list_scope_host_ids_params_list, get_data=lambda x: x
        )
        host_ids_gby_policy_id = {
            policy_scope_info["policy_id"]: policy_scope_info["bk_host_ids"] for policy_scope_info in policy_scope_infos
        }
        procs_exceed_max_retry_times = models.ProcessStatus.objects.filter(
            source_id__in=[str(policy_id) for policy_id in policy_ids],
            retry_times__gt=MAX_RETRY_TIME,
            bk_host_id__in=set(chain(*list(host_ids_gby_policy_id.values()))),
        ).values("source_id", "bk_host_id")
        abnormal_host_ids_gby_policy_id = defaultdict(set)

        for proc in procs_exceed_max_retry_times:
            abnormal_host_ids_gby_policy_id[int(proc["source_id"])].add(proc["bk_host_id"])

        # 过滤存在于ProcessStatus但实际已不在策略范围内主机ID
        # 出现上述问题的原因：1. 策略调整目标对范围外机器执行停用失败（ProcessStatus记录没有清掉）
        # 2. 本地CMDB缓存落后，list_scope_host_ids 拉取到最新的数据
        # TODO 问题1导致ProcessStatus中source_id关联机器并非策略实际范围，如果解决该问题，这部分逻辑的效率能大幅提升，考虑巡检清冗余
        # 问题2符合预期，若在CMDB裁剪一批机器，这部分机器本身已从策略移除，交由巡检处理
        for policy_id, host_ids in host_ids_gby_policy_id.items():
            abnormal_host_ids: Optional[Set[int]] = abnormal_host_ids_gby_policy_id.get(policy_id)
            if not abnormal_host_ids:
                abnormal_host_ids_gby_policy_id[policy_id] = set()
                continue
            abnormal_host_ids_gby_policy_id[policy_id] = abnormal_host_ids & set(host_ids)

        policy_id__abnormal_info_map = {}

        for policy in policies:
            abnormal_host_id_list = list(abnormal_host_ids_gby_policy_id[policy["id"]])
            abnormal_info = {
                "abnormal_host_ids": abnormal_host_id_list,
                "abnormal_host_count": len(abnormal_host_id_list),
            }
            policy_id__abnormal_info_map[policy["id"]] = abnormal_info

        return policy_id__abnormal_info_map
