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
import re
from collections import ChainMap
from typing import Any, Callable, Dict, List, Tuple

from django.conf import settings
from django.db import connection
from django.utils.translation import ugettext as _

from apps.node_man import constants, exceptions, models, tools
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.gse_package import gse_package_handler
from apps.node_man.handlers.install_channel import InstallChannelHandler
from apps.node_man.models import GsePackages
from apps.node_man.permissions.package_manage import PackageManagePermission
from apps.node_man.tools import JobTools
from apps.utils import APIModel


class MetaHandler(APIModel):
    """
    Meta处理器
    """

    def filter_empty_children(self, condition_result):
        """
        若没有数据，则过滤掉整个字段
        :condition_result: 条件数据
        :return: 过滤后的返回值
        """
        new_condition_result = []
        for condition in condition_result:
            if "children" not in condition:
                new_condition_result.append(condition)
            elif condition["children"] != []:
                new_condition_result.append(condition)
        return new_condition_result

    def regular_agent_version(self, agent_versions):
        """
        统一规范化Agent版本
        :param agent_versions: Agent版本
        :return: 升序后的版本列表
        """

        sort_map = {}
        # 1.60.58
        standard_format = re.compile("(.*)\\.(.*)\\.(.*)")
        # V0.01R060P42
        special_format = re.compile("V(.*)R(.*)[P|D](.*)?W")
        for version in agent_versions:
            version = version.upper()
            if "V" in version:
                result = special_format.findall(version)
                # 处理V0.01这样的数字
            else:
                result = standard_format.findall(version)

            if result != []:
                try:
                    numbers = result[0]
                    first_number = float(numbers[0])
                    if first_number < 1:
                        # 处理0.01这样的数字
                        first_number = first_number * 100
                    sort_map[version] = int(first_number) * 10000 + int(numbers[1]) * 100 + int(numbers[2])
                except BaseException:
                    # 捕捉特殊字符异常
                    sort_map[version] = constants.JOB_MAX_VALUE
            else:
                sort_map[version] = constants.JOB_MAX_VALUE

        return [item[0] for item in sorted(sort_map.items(), key=lambda item: item[1])]

    def fetch_host_process_unique_col(
        self,
        biz_permission: list,
        col_list: list,
        node_types: list,
        name: str = models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
        proc_type: str = "AGENT",
    ):
        """
        返回Host和process_status中指定列的唯一值
        :param biz_permission: 用户有权限的业务
        :param col_list: 指定列
        :param node_types: 节点类型
        :param name: process 名
        :return: 列的唯一值，数组
        """

        node_type = "'" + "','".join(node_types) + "'"
        biz_permission = ", ".join(str(biz) for biz in biz_permission)
        if not biz_permission:
            biz_permission = "''"
        select_sql = "SELECT distinct "
        select_conditions = []
        for col in col_list:
            if col in ["version", "status"]:
                select_conditions.append(f"{models.ProcessStatus._meta.db_table}.{col} AS `{col}`")
            else:
                select_conditions.append(f"{models.Host._meta.db_table}.{col} AS `{col}`")
        select_sql += ",".join(select_conditions)
        cursor = connection.cursor()
        cursor.execute(
            f"{select_sql} "
            f"FROM `{models.Host._meta.db_table}` join `{models.ProcessStatus._meta.db_table}` "
            f"on `{models.Host._meta.db_table}`.bk_host_id = `{models.ProcessStatus._meta.db_table}`.bk_host_id "
            f"WHERE (`{models.Host._meta.db_table}`.`node_type` IN ({node_type}) "
            f"AND `{models.Host._meta.db_table}`.`bk_biz_id` IN ({biz_permission}) "
            f"AND `{models.ProcessStatus._meta.db_table}`.`proc_type` = '{proc_type}' "
            f"AND `{models.ProcessStatus._meta.db_table}`.`name` = '{name}');"
        )

        return cursor

    def fetch_host_condition(self):
        """
        获取Host接口的条件
        :param username: 用户名
        :return: Host接口所有条件
        """

        # 用户有权限的业务
        biz_id_name = CmdbHandler().biz_id_name({"action": constants.IamActionType.agent_view})
        biz_permission = list(biz_id_name.keys())

        bk_cloud_ids = set()
        os_types = set()
        is_manuals = set()
        statuses = set()
        versions = set()

        col_map = [bk_cloud_ids, os_types, is_manuals, statuses, versions]
        # 获得数据
        col_list = ["bk_cloud_id", "os_type", "is_manual", "status", "version"]
        col_data = self.fetch_host_process_unique_col(
            biz_permission, col_list, [constants.NodeType.AGENT, constants.NodeType.PAGENT]
        )
        for sublist in col_data:
            for index, item in enumerate(sublist):
                col_map[index].add(item)

        os_types_children = self.fetch_os_type_children(tuple(os_types))
        statuses_children = [
            {"name": constants.PROC_STATUS_CHN.get(status, status), "id": status} for status in statuses if status != ""
        ]
        versions_children = [{"name": version, "id": version} for version in versions if version != ""]
        is_manual_children = [{"name": _("手动") if is_manual else _("远程"), "id": is_manual} for is_manual in is_manuals]
        bk_cloud_names = CloudHandler().list_cloud_info(bk_cloud_ids)
        bk_cloud_ids_children = [
            {"name": bk_cloud_names.get(bk_cloud_id, {}).get("bk_cloud_name", bk_cloud_id), "id": bk_cloud_id}
            for bk_cloud_id in bk_cloud_ids
        ]
        install_channel_children = [
            {"name": install_channel["name"], "id": install_channel["id"]}
            for install_channel in InstallChannelHandler.list()
        ]
        bk_addressing_children = [
            {"name": alias, "id": val}
            for val, alias in constants.CmdbAddressingType.get_member_value__alias_map().items()
        ]
        condition_value = [0, 1]
        enable_compression_children = [
            {"name": _("启用") if bool(condition) else _("停用"), "id": str(bool(condition))}
            for condition in condition_value
        ]
        bt_node_detection_children = [
            {"name": _("启用") if bool(condition) else _("停用"), "id": condition} for condition in condition_value
        ]
        condition_result_list = [
            {"name": _("IP"), "id": "ip"},
            {"name": _("管控区域ID:IP"), "id": "bk_cloud_ip"},
            {"name": _("主机名称"), "id": "bk_host_name"},
            {"name": _("管控区域"), "id": "bk_cloud_id", "children": bk_cloud_ids_children},
            {"name": _("安装通道"), "id": "install_channel_id", "children": install_channel_children},
            {"name": _("操作系统"), "id": "os_type", "children": os_types_children + [{"name": _("其它"), "id": "none"}]},
            {"name": _("Agent状态"), "id": "status", "children": statuses_children},
            {"name": _("Agent版本"), "id": "version", "children": versions_children},
            {"name": _("安装方式"), "id": "is_manual", "children": is_manual_children},
            {"name": _("BT节点探测"), "id": "bt_node_detection", "children": bt_node_detection_children},
            {"name": _("寻址方式"), "id": "bk_addressing", "children": bk_addressing_children},
        ]
        if settings.BKAPP_ENABLE_DHCP:
            condition_result_list.insert(
                10, {"name": _("数据压缩"), "id": "enable_compression", "children": enable_compression_children}
            )
        return self.filter_empty_children(condition_result_list)

    def fetch_job_list_condition(self, job_category, params=None):
        """
        获取任务历史接口的条件
        :return: Host接口所有条件
        """
        params = params or {}
        kwargs = {
            "start_time__gte": params.get("start_time"),
            "start_time__lte": params.get("end_time"),
        }

        # 获得业务id与名字的映射关系(用户有权限获取的业务)
        all_biz_info = CmdbHandler().biz_id_name_without_permission()
        biz_info = CmdbHandler().biz_id_name({"action": constants.IamActionType.task_history_view})
        biz_permission = list(biz_info.keys())

        if job_category == "job":
            job_type = constants.JOB_TUPLE
        else:
            job_type = constants.JOB_TYPE_MAP[job_category.split("_")[0]]

        try:
            job_result = JobTools.get_job_queryset_with_biz_scope(
                all_biz_info, biz_info, biz_permission, params.get("bk_biz_ids"), kwargs
            )
        except ValueError:
            return self.filter_empty_children(
                [
                    {"name": _("任务ID"), "id": "job_id"},
                    {"name": _("IP"), "id": "inner_ip_list"},
                ]
            )

        job_result = job_result.filter(job_type__in=job_type).values_list(
            "created_by", "job_type", "status", "subscription_id"
        )

        # 初始化各个条件集合
        created_bys = set()
        job_types = set()
        statuses = set()
        subscription_ids = set()

        for created_by, job_type, status, subscription_id in job_result:
            created_bys.add(created_by)
            job_types.add(job_type)
            statuses.add(status)
            subscription_ids.add(subscription_id)

        created_bys_children = [
            {"name": created_by, "id": created_by} for created_by in created_bys if created_by != ""
        ]

        statuses_children = [
            {"name": dict(constants.JobStatusType.get_choices()).get(status, status), "id": status}
            for status in statuses
        ]

        # 拆分任务类型为：订阅步骤类型（SaaS中简称为任务类型） & 操作类型
        step_types = set()
        op_types = set()
        for job_type in job_types:
            job_type_info = tools.JobTools.unzip_job_type(job_type)
            step_types.add(job_type_info["step_type"])
            op_types.add(job_type_info["op_type"])

        step_types_children = [
            {"name": constants.SUB_STEP_ALIAS_MAP.get(step_type, step_type), "id": step_type}
            for step_type in step_types
        ]

        op_types_children = [
            {"name": constants.OP_TYPE_ALIAS_MAP.get(op_type, op_type), "id": op_type} for op_type in op_types
        ]

        # 填充策略名称的筛选项
        policy_names_in_filter_condition = set(
            models.Subscription.objects.filter(
                id__in=subscription_ids, show_deleted=True, category=models.Subscription.CategoryType.POLICY
            ).values_list("name", flat=True)
        )
        policy_name_children = [
            {"name": policy_name, "id": policy_name}
            for policy_name in set(policy_names_in_filter_condition)
            if policy_name
        ]

        return self.filter_empty_children(
            [
                {"name": _("任务ID"), "id": "job_id"},
                {"name": _("IP"), "id": "inner_ip_list"},
                {"name": _("执行者"), "id": "created_by", "children": created_bys_children},
                {"name": _("执行状态"), "id": "status", "children": statuses_children},
                {"name": _("任务类型"), "id": "step_type", "children": step_types_children},
                {"name": _("操作类型"), "id": "op_type", "children": op_types_children},
                {"name": _("策略名称"), "id": "policy_name", "children": policy_name_children},
            ]
        )

    def fetch_plugin_list_condition(self):
        """
        获取插件接口的条件
        :return: Host接口所有条件
        """

        # 用户有权限的业务
        biz_id_name = CmdbHandler().biz_id_name({"action": constants.IamActionType.plugin_view})
        biz_permission = list(biz_id_name.keys())

        # 初始化各个条件集合
        plugin_names = tools.PluginV2Tools.fetch_head_plugins()
        plugin_result = {}

        # 获得数据
        bk_cloud_tuple = self.fetch_host_process_unique_col(biz_permission, ["bk_cloud_id"], ["AGENT", "PAGENT"])
        bk_cloud_ids = [bk_cloud[0] for bk_cloud in bk_cloud_tuple]
        bk_cloud_names = CloudHandler().list_cloud_info(bk_cloud_ids)
        plugin_result["bk_cloud_id"] = {
            "name": _("管控区域"),
            "value": [
                {"name": bk_cloud_names.get(bk_cloud_id, {}).get("bk_cloud_name", bk_cloud_id), "id": bk_cloud_id}
                for bk_cloud_id in bk_cloud_ids
            ],
        }

        os_type_tuple = self.fetch_host_process_unique_col(biz_permission, ["os_type"], ["AGENT", "PAGENT"])
        os_types = [os_type[0] for os_type in os_type_tuple]
        plugin_result["os_type"] = {
            "name": _("操作系统"),
            "value": [{"name": constants.OS_CHN.get(os, os), "id": os} for os in os_types if os != ""],
        }

        agent_version_tuple = self.fetch_host_process_unique_col(biz_permission, ["version"], ["AGENT", "PAGENT"])
        versions = self.regular_agent_version([version[0] for version in agent_version_tuple])
        plugin_result[models.ProcessStatus.GSE_AGENT_PROCESS_NAME] = {
            "name": _("Agent版本"),
            "value": [{"name": version, "id": version} for version in versions if version != ""],
        }

        status_tuple = self.fetch_host_process_unique_col(biz_permission, ["status"], ["AGENT", "PAGENT"])
        statuses = [statuse[0] for statuse in status_tuple]
        plugin_result["status"] = {
            "name": _("Agent状态"),
            "value": [
                {"name": constants.PROC_STATUS_CHN.get(status, status), "id": status}
                for status in statuses
                if status != ""
            ],
        }

        # 各个插件的版本
        for plugin_name in plugin_names:
            plugin_version_tuple = self.fetch_host_process_unique_col(
                biz_permission, ["version"], ["AGENT", "PAGENT", "PROXY"], name=plugin_name, proc_type="PLUGIN"
            )
            plugin_versions = [plugin_version[0] for plugin_version in plugin_version_tuple]
            plugin_result[plugin_name] = {"name": plugin_name, "value": [{"name": _("无版本"), "id": -1}]}
            plugin_result["{}_status".format(plugin_name)] = {
                "name": _("{}状态").format(plugin_name),
                "value": [
                    {"name": _("正常"), "id": constants.ProcStateType.RUNNING},
                    {"name": _("异常"), "id": constants.ProcStateType.TERMINATED},
                    {"name": _("未注册"), "id": constants.ProcStateType.UNREGISTER},
                ],
            }
            for plugin_version in plugin_versions:
                if plugin_version:
                    plugin_result[plugin_name]["value"].append({"name": plugin_version, "id": plugin_version})

        # 返回值
        ret_value = [{"name": "IP", "id": "ip"}]
        ret_value.extend(
            [
                {
                    "name": plugin_result[name]["name"],
                    "id": name if name != models.ProcessStatus.GSE_AGENT_PROCESS_NAME else "version",
                    "children": list(plugin_result[name]["value"]),
                }
                for name in plugin_result
            ]
        )

        return self.filter_empty_children(ret_value)

    @staticmethod
    def fetch_plugin_host_condition():
        ret_value = [
            {"name": "IP", "id": "ip"},
            {"name": _("管控区域ID:IP"), "id": "bk_cloud_ip"},
            {"name": _("主机名称"), "id": "bk_host_name"},
            {
                "id": "node_type",
                "name": _("节点类型"),
                "children": [
                    {"id": node_type, "name": constants.NODE_TYPE_ALIAS_MAP.get(node_type)}
                    for node_type in constants.NODE_TUPLE
                ],
            },
        ]

        clouds = dict(models.Cloud.objects.values_list("bk_cloud_id", "bk_cloud_name"))
        cloud_children = [{"id": cloud_id, "name": cloud_name} for cloud_id, cloud_name in clouds.items()]
        cloud_children.insert(0, {"id": constants.DEFAULT_CLOUD, "name": _("直连区域")})
        ret_value.append({"name": _("管控区域"), "id": "bk_cloud_id", "children": cloud_children})

        os_dict = {"name": _("操作系统"), "id": "os_type", "children": []}
        for os_type in constants.OS_TUPLE:
            if os_type == constants.OsType.SOLARIS and settings.BKAPP_RUN_ENV == constants.BkappRunEnvType.CE.value:
                continue
            os_dict["children"].append({"id": os_type, "name": constants.OS_CHN.get(os_type, os_type)})
        ret_value.append(os_dict)

        # Agent状态
        ret_value.append(
            {
                "id": "status",
                "name": _("Agent状态"),
                "children": [
                    {"id": status, "name": constants.PROC_STATUS_CHN[status]}
                    for status in constants.PROC_STATUS_DICT.values()
                ],
            }
        )

        bt_node_detection_children = [
            {"name": _("启用") if bool(condition) else _("停用"), "id": condition} for condition in [0, 1]
        ]

        enable_compression_children = [
            {"name": _("启用") if bool(condition) else _("停用"), "id": str(bool(condition))} for condition in [0, 1]
        ]
        ret_value.append({"name": _("BT节点探测"), "id": "bt_node_detection", "children": bt_node_detection_children})

        if settings.BKAPP_ENABLE_DHCP:
            ret_value.append({"name": _("数据压缩"), "id": "enable_compression", "children": enable_compression_children})

        bk_addressing_children = [
            {"name": alias, "id": val}
            for val, alias in constants.CmdbAddressingType.get_member_value__alias_map().items()
        ]
        ret_value.append({"name": _("寻址方式"), "id": "bk_addressing", "children": bk_addressing_children})

        ret_value.extend(
            [
                {
                    "id": plugin_name,
                    "name": plugin_name,
                    # 数据量较大的情况下，children获取较慢，此处插件的children设置为空，由前端异步请求获取
                    "children": [],
                }
                for plugin_name in tools.PluginV2Tools.fetch_head_plugins()
            ]
        )

        return ret_value

    @staticmethod
    def fetch_plugin_version_condition():
        plugin_names = tools.PluginV2Tools.fetch_head_plugins()
        versions = (
            models.ProcessStatus.objects.filter(
                source_type=models.ProcessStatus.SourceType.DEFAULT,
                name__in=plugin_names + [models.ProcessStatus.GSE_AGENT_PROCESS_NAME],
            )
            .values("name", "version")
            .exclude(version="")
            .distinct()
        )
        plugin_version = {}
        for version in versions:
            plugin_version.setdefault(version["name"], []).append(
                {"id": version["version"], "name": version["version"]}
            )

        plugin_result = [
            {
                "name": _("Agent版本"),
                "id": "version",
                "children": sorted(
                    plugin_version.get(models.ProcessStatus.GSE_AGENT_PROCESS_NAME, []),
                    key=lambda keys: keys["name"],
                    reverse=True,
                ),
            }
        ]

        for name in plugin_names:
            plugin_result.append(
                {
                    "name": _("{name}版本").format(name=name),
                    "id": name,
                    "children": [{"name": _("无版本"), "id": -1}]
                    + sorted(plugin_version.get(name, []), key=lambda keys: keys["name"], reverse=True),
                }
            )
            plugin_result.append(
                {
                    "name": _("{}状态").format(name),
                    "id": f"{name}_status",
                    "children": [
                        {"name": constants.PROC_STATUS_CHN.get(proc_status, proc_status), "id": proc_status}
                        for proc_status in constants.PROC_STATUS_TO_BE_DISPLAYED
                    ],
                }
            )

        return plugin_result

    @staticmethod
    def fetch_os_type_children(os_types: Tuple = constants.OsType):
        os_type_children = []
        for os_type in os_types:
            if os_type == "":
                continue
            os_type_children.append({"id": os_type, "name": constants.OS_CHN.get(os_type, os_type)})
        return os_type_children

    @staticmethod
    def fetch_agent_pkg_manager_children(params=None):
        params: Dict[str, Any] = params or {}
        project: str = params.get("project", "gse_agent")

        if not PackageManagePermission().has_permission(None, None):
            raise exceptions.PermissionDeniedError(_("该用户不是管理员"))

        versions, tag_description__name_map, creators, is_readys = set(), dict(), set(), set()
        gse_packages = GsePackages.objects.filter(project=project).values("version", "created_by", "is_ready")
        for p in gse_packages:
            tags: List[Dict[str, Any]] = gse_package_handler.get_tags(
                version=p["version"],
                project=project,
                to_top=True,
                use_cache=True,
                unique=True,
                get_template_tags=True,
            )
            versions.add(p["version"])
            creators.add(p["created_by"])
            is_readys.add(p["is_ready"])

            for t in tags:
                description, name = t.get("description", ""), t.get("name", "")
                if description in tag_description__name_map and len(name) > len(tag_description__name_map[description]):
                    # 取模板标签，模板标签的name长度最小，实例标签为{{ 模板标签 }}_{{ target_version }}
                    continue

                tag_description__name_map[description] = name

        return [
            {
                "name": _("版本号"),
                "id": "version",
                "children": [
                    {
                        "id": version,
                        "name": version,
                    }
                    for version in versions
                ],
            },
            {
                "name": _("标签信息"),
                "id": "tag_names",
                "children": [
                    {
                        "id": tag_name,
                        "name": tag_description,
                    }
                    for tag_description, tag_name in tag_description__name_map.items()
                ],
            },
            {
                "name": _("上传用户"),
                "id": "creator",
                "children": [
                    {
                        "id": creator,
                        "name": creator,
                    }
                    for creator in creators
                ],
            },
            {
                "name": _("状态"),
                "id": "is_ready",
                "children": [
                    {
                        "id": is_ready,
                        "name": constants.GSE_PACKAGE_ENABLE_ALIAS_MAP.get(is_ready, is_ready),
                    }
                    for is_ready in is_readys
                ],
            },
        ]

    def filter_condition(self, category, params=None):
        """
        获取过滤条件
        :param category: 接口, host, cloud, Job等
        :param params: 请求参数的字典
        :return: 某接口所有条件
        """

        if category == "host":
            return self.fetch_host_condition()
        elif category == "job":
            return self.fetch_job_list_condition("job", params=params)
        elif category == "agent_job":
            return self.fetch_job_list_condition("agent_job")
        elif category == "proxy_job":
            return self.fetch_job_list_condition("proxy_job")
        elif category == "plugin_job":
            return self.fetch_job_list_condition("plugin_job")
        elif category == "plugin_version":
            ret = self.fetch_plugin_version_condition()
            return ret
        elif category == "plugin_host":
            ret = self.fetch_plugin_host_condition()
            return ret
        elif category == "os_type":
            ret = self.fetch_os_type_children()
            return ret
        elif category == "agent_pkg_manage":
            return self.fetch_agent_pkg_manager_children(params=params)

    @staticmethod
    def install_default_values_formatter(install_default_values: Dict[str, Dict[str, Any]]):
        """
        安装参数默认值格式化器
        auth_type, account, port, retention, peer_exchange_switch_for_agent, bt_speed_limit, data_path
        字段含义参考：apps/node_man/serializers/job.py HostSerializer
        :return:
        {
            "COMMON": {
                "auth_type": "KEY"
            },
            "WINDOWS": {
                "port": 445,
                "auth_type": "PASSWORD",
                "account": "Administrator"
            },
            "LINUX": {
                "port": 22,
                "auth_type": "KEY",
                "account": "root"
            },
            "AIX": {
                "port": 22,
                "auth_type": "KEY",
                "account": "root"
            },
            "SOLARIS": {
                "port": 22,
                "auth_type": "KEY",
                "account": "root"
            }
        }
        """
        common_values = install_default_values.get("COMMON", {})

        for os_type in constants.OS_TUPLE:
            default_values = {}
            if os_type in [constants.OsType.WINDOWS]:
                default_values.update({"port": constants.WINDOWS_PORT, "account": constants.WINDOWS_ACCOUNT})
            else:
                default_values.update({"port": settings.BKAPP_DEFAULT_SSH_PORT, "account": constants.LINUX_ACCOUNT})

            # 取值顺序：全局变量所设置的值 -> 公共默认值（COMMON） -> 默认值
            install_default_values[os_type] = dict(
                ChainMap(install_default_values.get(os_type, {}), common_values, default_values)
            )

        return install_default_values

    def search(self, key):
        """
        查询相关配置
        """
        setting_name__formatter_map: Dict[str, Callable] = {
            models.GlobalSettings.KeyEnum.INSTALL_DEFAULT_VALUES.value: self.install_default_values_formatter
        }
        setting_kv = dict(models.GlobalSettings.objects.filter(key=key).values_list("key", "v_json"))

        formatted_setting_kv = {}
        for setting_name, setting_value in setting_kv.items():
            formatter = setting_name__formatter_map.get(setting_name, lambda v: v)
            formatted_setting_kv[setting_name] = formatter(setting_value)

        return formatted_setting_kv

    def job_setting(self, params):
        """
        查询相关配置
        :param params: 请求参数
        """

        user_setting = {}
        for setting in params:
            user_setting[setting] = params[setting]
        global_setting, state = models.GlobalSettings.objects.get_or_create(
            key="job_settings", defaults={"v_json": user_setting}
        )

        if not state:
            # 如果已经有相关配置
            user_setting = global_setting.v_json
            for setting in params:
                user_setting[setting] = params[setting]
            global_setting.v_json = user_setting
            global_setting.save()
