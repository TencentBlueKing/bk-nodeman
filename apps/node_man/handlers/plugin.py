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
from collections import defaultdict
from typing import Any, Dict

from django.db.models import Q
from django.utils.translation import get_language

from apps.core.tag import targets
from apps.core.tag.models import Tag
from apps.node_man import constants as const
from apps.node_man import tools
from apps.node_man.constants import IamActionType
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.host import HostHandler
from apps.node_man.handlers.validator import operate_validator
from apps.node_man.models import (
    Cloud,
    GsePluginDesc,
    Host,
    JobTask,
    Packages,
    PluginConfigTemplate,
    ProcControl,
    ProcessStatus,
    Subscription,
    SubscriptionTask,
)
from apps.utils import APIModel
from common.api import NodeApi


class PluginHandler(APIModel):
    """
    插件处理器
    """

    @staticmethod
    def get_meta_info(process_status_objs):
        source_ids = []
        plugin_name = []
        plugin_version = []
        for _plugin in process_status_objs:
            source_ids.append(_plugin["source_id"])
            plugin_name.append(_plugin["name"])
            plugin_version.append(_plugin["version"])

        # 查询所有相关联的插件包信息
        packages = Packages.objects.filter(project__in=plugin_name, version__in=plugin_version).values()
        package_version_map = {}
        package_ids = []
        for package in packages:
            package_version_map[f"{package['project']}{package['version']}"] = package
            package_ids.append(package["id"])

        # 查询插件包控制信息
        proc_control = ProcControl.objects.filter(plugin_package_id__in=package_ids).values()
        package_control_map = {}
        for control in proc_control:
            package_control_map[control["plugin_package_id"]] = control

        # 查询插件包配置文件
        package_templates = PluginConfigTemplate.objects.filter(
            plugin_name__in=plugin_name, plugin_version__in=plugin_version
        ).values()
        package_version_template_map = {}
        for package in package_templates:
            package_version_template_map[f"{package['plugin_name']}{package['plugin_version']}"] = package

        # 查询所有订阅任务的is_auto_trigger字段
        subscription_tasks = SubscriptionTask.objects.filter(subscription_id__in=source_ids).values(
            "subscription_id", "is_auto_trigger"
        )
        subscription_id_auto_trigger_map = {}
        for subscription_task in subscription_tasks:
            subscription_id_auto_trigger_map[subscription_task["subscription_id"]] = subscription_task[
                "is_auto_trigger"
            ]

        # 查询所有订阅任务的名字
        subscription_id_name_map = {}
        subscriptions = Subscription.objects.filter(id__in=source_ids, category="policy").values(
            "id", "name", "update_time"
        )
        for subscription in subscriptions:
            subscription_id_name_map[str(subscription["id"])] = subscription

        return {
            "package_version_map": package_version_map,
            "package_control_map": package_control_map,
            "package_version_template_map": package_version_template_map,
            "subscription_id_auto_trigger_map": subscription_id_auto_trigger_map,
            "subscription_id_name_map": subscription_id_name_map,
        }

    @staticmethod
    def get_host_subscription_plugins(bk_host_ids):
        # 获取每个host下的订阅任务
        subscription_plugin_dict = {}
        subscription_plugins = ProcessStatus.objects.filter(
            bk_host_id__in=bk_host_ids, source_type="subscription"
        ).values("bk_host_id", "status", "version", "source_id", "name", "id")

        meta = PluginHandler.get_meta_info(subscription_plugins)

        for plugin in subscription_plugins:
            plugin_version_key = f"{plugin['name']}{plugin['version']}"
            if not meta["subscription_id_name_map"].get(plugin["source_id"]):
                continue
            subscription_name = meta["subscription_id_name_map"][plugin["source_id"]]["name"] or "--"
            update_time = meta["subscription_id_name_map"][plugin["source_id"]]["update_time"]
            bk_host_data = subscription_plugin_dict.get(plugin["bk_host_id"])

            # 子任务
            subscription_task = {
                "id": plugin["id"],
                "plugin_name": plugin["name"],
                "name": subscription_name,
                "status": plugin["status"],
                "version": plugin["version"],
                "update_time": update_time,
                "is_auto_trigger": meta["subscription_id_auto_trigger_map"][int(plugin["source_id"])],
                "deploy_type": meta["package_version_map"].get(plugin_version_key, {}).get("deploy_type", "--"),
                "config_template": meta["package_version_template_map"].get(plugin_version_key, {}).get("name", "--"),
                "config_template_version": meta["package_version_template_map"]
                .get(plugin_version_key, {})
                .get("version", "--"),
                "install_path": (
                    meta["package_control_map"]
                    .get(meta["package_version_map"].get(plugin_version_key, {}).get("id", "--"), {})
                    .get("install_path", "--")
                ),
            }

            if bk_host_data and plugin["name"] in bk_host_data:
                subscription_plugin_dict[plugin["bk_host_id"]][plugin["name"]]["subscription_statistics"][
                    plugin["status"].lower()
                ] += 1
                subscription_plugin_dict[plugin["bk_host_id"]][plugin["name"]]["subscription_tasks"].append(
                    subscription_task
                )
                continue
            elif not bk_host_data:
                subscription_plugin_dict[plugin["bk_host_id"]] = {}

            statistics = {
                "running": 0,
                "unknown": 0,
                "terminated": 0,
                "not_installed": 0,
            }
            statistics[plugin["status"].lower()] += 1
            subscription_plugin_dict[plugin["bk_host_id"]][plugin["name"]] = {
                "subscription_statistics": statistics,
                "subscription_tasks": [subscription_task],
            }
        return subscription_plugin_dict

    @staticmethod
    def list(params: Dict[str, Any]):
        """
        查询主机
        :param params: 经校验后的数据
        """

        # 用户有权限获取的业务
        # 格式 { bk_biz_id: bk_biz_name , ...}
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.plugin_view})

        # 用户主机操作权限
        plugin_operate_bizs = CmdbHandler().biz_id_name({"action": IamActionType.plugin_operate})

        # 页面
        if params["pagesize"] != -1:
            # 如果是正常数量
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
        else:
            # 全部
            begin = None
            end = None
            # 跨页全选模式，仅返回用户有权限操作的主机
            user_biz = plugin_operate_bizs

        # 查询
        hosts_status_sql = (
            HostHandler()
            .multiple_cond_sql(params, user_biz, plugin=True)
            .exclude(bk_host_id__in=params.get("exclude_hosts", []))
        )

        # 计算总数
        hosts_status_count = hosts_status_sql.count()

        if params.get("simple"):
            host_simples = list(hosts_status_sql[begin:end].values("bk_host_id", "bk_biz_id"))
            return {"total": len(host_simples), "list": host_simples}

        if params.get("only_ip"):
            # 如果仅需要IP数据
            hosts_status = [host["inner_ip"] for host in list(hosts_status_sql[begin:end].values("inner_ip"))]
            result = {"total": hosts_status_count, "list": hosts_status}
            return result
        else:
            # sql分页查询获得数据
            hosts_status = list(
                hosts_status_sql[begin:end].values(
                    "bk_biz_id",
                    "bk_host_id",
                    "bk_cloud_id",
                    "bk_host_name",
                    "bk_addressing",
                    "inner_ip",
                    "inner_ipv6",
                    "os_type",
                    "cpu_arch",
                    "node_type",
                    "node_from",
                )
            )

        # 分页结果的Host_id, cloud_id集合
        bk_host_ids = [hs["bk_host_id"] for hs in hosts_status]
        bk_cloud_ids = [hs["bk_cloud_id"] for hs in hosts_status]

        # 获得云区域名称
        cloud_name = dict(
            Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values_list("bk_cloud_id", "bk_cloud_name")
        )
        cloud_name[0] = const.DEFAULT_CLOUD_NAME

        # 获得 Job Result 数据
        job_status = JobTask.objects.filter(bk_host_id__in=bk_host_ids).values(
            "bk_host_id", "instance_id", "job_id", "status", "current_step"
        )
        host_id_job_status = {
            status["bk_host_id"]: {
                "instance_id": status["instance_id"],
                "job_id": status["job_id"],
                "status": status["status"],
                "current_step": status["current_step"],
            }
            for status in job_status
        }

        # 获得每个Host下的插件
        host_plugin = defaultdict(list)
        agent_status = dict()
        plugins = ProcessStatus.objects.filter(
            Q(source_type=ProcessStatus.SourceType.DEFAULT, is_latest=True)
            | Q(source_type=ProcessStatus.SourceType.DEFAULT, proc_type=const.ProcType.AGENT),
            bk_host_id__in=bk_host_ids,
        ).values()
        for plugin in plugins:
            if plugin["proc_type"] == const.ProcType.AGENT:
                if plugin["name"] == ProcessStatus.GSE_AGENT_PROCESS_NAME:
                    agent_status[plugin["bk_host_id"]] = {"status": plugin["status"], "version": plugin["version"]}
                continue
            host_plugin[plugin["bk_host_id"]].append(
                {
                    "name": plugin["name"],
                    "status": plugin["status"],
                    "version": plugin["version"],
                    "host_id": plugin["bk_host_id"],
                }
            )

        # 汇总
        for hs in hosts_status:
            bk_host_id = hs["bk_host_id"]
            hs.update(agent_status.get(bk_host_id, {}))
            hs["status_display"] = const.PROC_STATUS_CHN.get(hs.get("status"), "")
            hs["node_type"] = const.NODE_TYPE_ALIAS_MAP.get(hs["node_type"])
            hs["bk_cloud_name"] = cloud_name.get(hs["bk_cloud_id"])
            hs["bk_biz_name"] = user_biz.get(hs["bk_biz_id"], "")
            hs["job_result"] = host_id_job_status.get(bk_host_id, {})
            hs["plugin_status"] = host_plugin.get(bk_host_id, [])
            hs["operate_permission"] = hs["bk_biz_id"] in plugin_operate_bizs

        result = {"total": hosts_status_count, "list": hosts_status}

        # 适配单个插件停用预览时的AGENT状态统计，性能不行
        if params.get("with_agent_status_counter"):
            result["agent_status_count"] = tools.HostV2Tools.get_agent_status_counter(
                ProcessStatus.objects.filter(
                    proc_type=const.ProcType.AGENT,
                    source_type=ProcessStatus.SourceType.DEFAULT,
                    bk_host_id__in=set(hosts_status_sql.values_list("bk_host_id", flat=True)),
                )
            )

        return result

    @staticmethod
    def operate(params: dict, username: str):
        """
        用于只有bk_host_id参数的插件操作
        :param params: 任务类型及host_id
        :param username: 用户名
        """

        # 用户有权限获取的业务
        # 格式 { bk_biz_id: bk_biz_name , ...}
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.plugin_operate})

        if params.get("exclude_hosts") is not None:
            # 跨页全选
            db_host_sql = (
                HostHandler()
                .multiple_cond_sql(params, user_biz, plugin=True)
                .exclude(bk_host_id__in=params.get("exclude_hosts", []))
                .values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")
            )

        else:
            # 不是跨页全选
            db_host_sql = Host.objects.filter(
                bk_host_id__in=params["bk_host_id"],
                node_type__in=[const.NodeType.AGENT, const.NodeType.PAGENT, const.NodeType.PROXY],
            ).values("bk_host_id", "bk_biz_id", "bk_cloud_id", "inner_ip", "node_type", "os_type")

        # 校验器进行校验
        db_host_ids, host_biz_scope = operate_validator(list(db_host_sql))

        plugin_name__job_id__map = {}
        for plugin_params in params["plugin_params_list"]:
            plugin_name, plugin_version = plugin_params["name"], plugin_params["version"]
            subscription_create_result = PluginHandler.create_subscription(
                job_type=params["job_type"],
                nodes=db_host_ids,
                name=plugin_name,
                version=plugin_version,
                keep_config=plugin_params.get("keep_config"),
                no_restart=plugin_params.get("no_restart"),
            )

            create_job_info = tools.JobTools.create_job(
                job_type=params["job_type"],
                subscription_id=subscription_create_result["subscription_id"],
                task_id=subscription_create_result["task_id"],
                bk_biz_scope=list(set(host_biz_scope)),
            )
            plugin_name__job_id__map[plugin_name] = create_job_info["job_id"]

        # 使用v2.0.x参数进行插件操作时，使用旧返回结构
        if params.get("plugin_params"):
            job_id = list(plugin_name__job_id__map.values())[0]
            return {"job_id": job_id, "job_url": tools.JobTools.get_job_url(job_id)}
        return plugin_name__job_id__map

    @staticmethod
    def create_subscription(
        job_type: str, nodes: list, name: str, version: str, keep_config: bool = None, no_restart: bool = None
    ):
        """

        创建插件订阅任务
        :param job_type: MAIN_JOB_PLUGIN
        :param nodes: 任务范围
        :param name: 插件名
        :param version: 插件版本
        :param keep_config: 保留原有配置
        :param no_restart: 不重启进程
        :return:
        """
        params = {
            "run_immediately": True,
            "bk_app_code": "nodeman",
            "bk_username": "admin",
            "plugin_name": name,
            "is_main": True,
            # 非策略订阅在SaaS侧定义为一次性下发操作
            "category": Subscription.CategoryType.ONCE,
            "scope": {"node_type": "INSTANCE", "object_type": "HOST", "nodes": nodes},
            "steps": [
                {
                    "config": {
                        "config_templates": [{"name": "{}.conf".format(name), "version": "latest", "is_main": True}],
                        "plugin_name": name,
                        "plugin_version": version,
                        "job_type": job_type,
                    },
                    "type": "PLUGIN",
                    "id": name,
                    "params": {
                        "keep_config": keep_config,
                        "no_restart": no_restart,
                        "blueking_language": get_language(),
                    },
                }
            ],
        }

        return NodeApi.create_subscription(params)

    @staticmethod
    def get_packages(project, os_type):
        """
        获取某个插件包列表
        """
        plugin_obj = GsePluginDesc.objects.get(name=project)

        # 查找置顶版本
        top_tag: Tag = targets.PluginTargetHelper.get_top_tag_or_none(plugin_obj.id)
        top_versions = []
        if top_tag is not None:
            top_versions = [top_tag.name]

        package_infos = tools.PluginV2Tools.fetch_package_infos(
            project=project, os_type=os_type.lower(), cpu_arch=const.CpuType.x86_64
        )
        return tools.PluginV2Tools.get_sorted_package_infos(package_infos, top_versions=top_versions)

    @staticmethod
    def get_process_status(bk_host_ids: list):
        """
        获取主机process状态信息
        """
        return ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids)

    @staticmethod
    def get_statistics():
        """
        统计各个插件的安装情况
        """
        hosts = Host.objects.all().values("bk_biz_id", "bk_host_id")

        host_biz_mappings = {host["bk_host_id"]: host["bk_biz_id"] for host in hosts}

        processes = ProcessStatus.objects.filter(source_type=ProcessStatus.SourceType.DEFAULT).values(
            "bk_host_id", "version", "name", "status"
        )

        process_count = defaultdict(int)

        for process in processes:
            if process["bk_host_id"] not in host_biz_mappings:
                continue
            # key: 业务ID，插件名称，插件版本，状态。按照这四个维度进行聚合
            key = (host_biz_mappings[process["bk_host_id"]], process["name"], process["version"], process["status"])
            process_count[key] += 1

        result = [
            {
                "bk_biz_id": bk_biz_id,
                "plugin_name": plugin_name,
                "version": version,
                "status": status,
                "host_count": host_count,
            }
            for (bk_biz_id, plugin_name, version, status), host_count in process_count.items()
        ]
        return result
