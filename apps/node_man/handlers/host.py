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
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.backend.tests.components.collections.agent.utils import DEFAULT_CLOUD_NAME
from apps.node_man import constants as const
from apps.node_man.constants import IamActionType
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    BusinessNotPermissionError,
    CloudNotPermissionError,
    HostIDNotExists,
    HostNotExists,
    IpInUsedError,
    NotHostPermission,
    PwdCheckError,
)
from apps.node_man.handlers.ap import APHandler
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.handlers.validator import update_pwd_validate
from apps.node_man.models import (
    AccessPoint,
    Cloud,
    GsePluginDesc,
    Host,
    IdentityData,
    InstallChannel,
    JobTask,
    ProcessStatus,
)
from apps.utils import APIModel
from apps.utils.basic import filter_values
from apps.utils.local import get_request_username


class HostHandler(APIModel):
    """
    Host处理器
    """

    def check_hosts_permission(self, bk_host_ids: list, permission_biz_ids: list):
        """
        在步骤开始前检查权限
        :param bk_host_ids: 主机ID
        :param permission_biz_ids: 用户有权限的业务ID
        :return permission_host_ids: 有权限的主机ID
        """

        permission_host_ids = []
        hosts = Host.objects.filter(bk_host_id__in=bk_host_ids).values(
            "bk_host_id", "bk_biz_id", "inner_ip", "bk_cloud_id"
        )

        # 获得所有Host的云区域
        bk_cloud_ids = [host["bk_cloud_id"] for host in hosts]

        # 获得所有云区域的权限
        cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

        for host in hosts:
            # 是否有业务权限
            if host["bk_biz_id"] in permission_biz_ids:
                permission_host_ids.append(host["bk_host_id"])

            # 云区域权限列表
            cloud_permissions = IamHandler().fetch_policy(get_request_username(), [IamActionType.cloud_view])[
                IamActionType.cloud_view
            ]
            cloud_permissions.append(const.DEFAULT_CLOUD)

            # 是否有云区域权限
            if host["bk_cloud_id"] not in cloud_permissions:
                raise CloudNotPermissionError(
                    _("您没有云区域 {bk_cloud_name} 的权限").format(
                        bk_cloud_name=cloud_info.get(host["bk_cloud_id"], {}).get("bk_cloud_name")
                    )
                )

        return permission_host_ids

    @classmethod
    def fuzzy_cond(cls, custom: str, wheres: list, sql_params: list):
        """
        用于生成模糊搜索的条件
        :param custom: 用户的输入
        :param wheres: Where 语句列表
        :param sql_params: escape 参数列表
        :return: where, sql_params
        """
        search_sql = f"{Host._meta.db_table}.inner_ip like %s"

        sql_params.extend([f"%{custom}%"])

        # 云区域搜索
        bk_cloud_names = CloudHandler().list_cloud_name()
        cloud_ids = [str(cloud) for cloud in bk_cloud_names if bk_cloud_names[cloud].find(custom) != -1]
        cloud_ids = ",".join(cloud_ids)
        # 如果存在云区域结果
        if cloud_ids:
            search_sql += f" OR {Host._meta.db_table}.bk_cloud_id in (%s)"
            sql_params.append(cloud_ids)

        wheres.append("(" + search_sql + ")")
        return wheres, sql_params

    @staticmethod
    def _handle_plugin_conditions(params, plugin_names, select):
        if not params.get("conditions"):
            return []

        bk_host_id_list = []
        init_wheres = [
            f"{Host._meta.db_table}.bk_host_id={ProcessStatus._meta.db_table}.bk_host_id",
            f'{ProcessStatus._meta.db_table}.proc_type="{const.ProcType.PLUGIN}"',
            f'{ProcessStatus._meta.db_table}.source_type="{ProcessStatus.SourceType.DEFAULT}"',
            f"{ProcessStatus._meta.db_table}.is_latest=true",
        ]
        wheres = []
        for condition in params["conditions"]:

            if condition["key"] == "source_id":
                placeholder = []
                for cond in condition["value"]:
                    placeholder.append('"{}"'.format(cond))
                wheres.append(f'{ProcessStatus._meta.db_table}.source_id in ({",".join(placeholder)})')

            if condition["key"] == "plugin_name":
                placeholder = []
                for cond in condition["value"]:
                    placeholder.append('"{}"'.format(cond))
                wheres.append(f'{ProcessStatus._meta.db_table}.name in ({",".join(placeholder)})')

            if condition["key"] in plugin_names:
                # 插件版本的精确搜索
                placeholder = []
                for cond in condition["value"]:
                    if cond == -1:
                        # 无版本插件筛选
                        placeholder.append('""')
                    else:
                        placeholder.append('"{}"'.format(cond))
                wheres.append(f'{ProcessStatus._meta.db_table}.version in ({",".join(placeholder)})')
                wheres.append(f'{ProcessStatus._meta.db_table}.name="{condition["key"]}"')

            elif condition["key"] in [f"{plugin}_status" for plugin in plugin_names]:
                # 插件状态的精确搜索
                placeholder = []
                for cond in condition["value"]:
                    placeholder.append('"{}"'.format(cond))
                wheres.append(f'{ProcessStatus._meta.db_table}.status in ({",".join(placeholder)})')
                wheres.append(f'{ProcessStatus._meta.db_table}.name="{"_".join(condition["key"].split("_")[:-1])}"')

        if wheres:
            wheres = init_wheres + wheres
            bk_host_id_list = set(
                Host.objects.extra(select=select, tables=[ProcessStatus._meta.db_table], where=wheres).values_list(
                    "bk_host_id", flat=True
                )
            )
            # 对于有搜索条件但搜索结果为空的情况，填充一个无效的主机ID（-1），用于兼容multiple_cond_sql将空列表当成全选的逻辑
            return bk_host_id_list or [-1]
        return bk_host_id_list

    @classmethod
    def multiple_cond_sql(cls, params: dict, user_biz: dict, proxy=False, plugin=False, return_all_node_type=False):
        """
        用于生成多条件sql查询
        :param return_all_node_type: 是否返回所有类型
        :param params: 条件数据
        :param user_biz: 用户权限列表
        :param proxy: 是否为代理
        :param plugin: 是否为插件
        :return: 根据条件查询的所有结果
        """
        select = {
            "status": f"{ProcessStatus._meta.db_table}.status",
            "version": f"{ProcessStatus._meta.db_table}.version",
        }

        # 插件查询条件
        has_conditional = False
        bk_host_id_list = []
        plugin_names = set(list(GsePluginDesc.objects.all().values_list("name", flat=True)) + settings.HEAD_PLUGINS)
        if plugin:
            bk_host_id_list = cls._handle_plugin_conditions(params, plugin_names, select)
            if bk_host_id_list:
                has_conditional = True

        # 查询参数设置，默认为Host接口搜索
        # 如果需要搜索插件版本，wheres[1]的proc_type将变动为PLUGIN
        sql_params = []
        init_wheres = [
            f"{Host._meta.db_table}.bk_host_id={ProcessStatus._meta.db_table}.bk_host_id",
            f'{ProcessStatus._meta.db_table}.proc_type="{const.ProcType.AGENT}"',
            f'{ProcessStatus._meta.db_table}.source_type="{ProcessStatus.SourceType.DEFAULT}"',
        ]
        wheres = []

        # 如果有带筛选条件，则只返回筛选且有权业务的主机, 否则返回用户所有有权限的业务的主机
        biz_permission = (
            [bk_biz_id for bk_biz_id in params["bk_biz_id"] if bk_biz_id in user_biz]
            if params.get("bk_biz_id")
            else list(user_biz.keys())
        )

        kwargs = {"bk_host_id__in": params.get("bk_host_id"), "bk_biz_id__in": list(biz_permission)}

        if proxy:
            # 单独查代理
            node_type = [const.NodeType.PROXY]
        elif plugin or return_all_node_type:
            # 查插件，或者返回全部类型的情况
            node_type = [const.NodeType.AGENT, const.NodeType.PAGENT, const.NodeType.PROXY]
        else:
            # 查Agent
            node_type = [const.NodeType.AGENT, const.NodeType.PAGENT]

        # 条件搜索
        where_or = []
        cond_host_ids = None
        all_query_biz = []

        for condition in params.get("conditions", []):
            if condition["key"] in ["inner_ip", "node_from", "node_type"]:
                # Host表的精确搜索(现主要为 os_type, inner_ip, bk_cloud_id)
                kwargs[condition["key"] + "__in"] = condition["value"]
            elif condition["key"] in ["os_type"]:
                # 如果传的是none，替换成""
                kwargs[condition["key"] + "__in"] = list(map(lambda x: "" if x == "none" else x, condition["value"]))

            elif condition["key"] in ["status", "version"]:
                # ProcessStatus表的精确搜索(现主要为 status, version)
                placeholder = []
                for cond in condition["value"]:
                    sql_params.append(cond)
                    placeholder.append("%s")
                wheres.append(f'{ProcessStatus._meta.db_table}.{condition["key"]} in ({",".join(placeholder)})')

            elif condition["key"] in ["is_manual", "bk_cloud_id", "install_channel_id"]:
                # 是否手动安装
                kwargs[condition["key"] + "__in"] = (
                    condition["value"] if "".join([str(v) for v in condition["value"]]).isdigit() else []
                )

            elif condition["key"] == "topology":
                # 集群与模块的精准搜索
                biz = condition["value"].get("bk_biz_id")
                if biz not in biz_permission:
                    # 对于单个拓扑查询条件，没有业务权限时bk_host_id__in不叠加即可
                    # 无需清空列表，否则之前累积的有权限的主机查询条件也会跟着被清空
                    continue
                sets = condition["value"].get("bk_set_ids", [])
                modules = condition["value"].get("bk_module_ids", [])
                # 传入拓扑是一个业务，无需请求cc，直接从数据库获取bk_host_id
                if len(sets) == 0 and len(modules) == 0:
                    all_query_biz.append(biz)
                    continue
                host_ids = CmdbHandler().fetch_host_ids_by_biz(biz, sets, modules)
                if cond_host_ids is None:
                    cond_host_ids = host_ids
                else:
                    cond_host_ids.extend(host_ids)

            elif condition["key"] == "query" and isinstance(condition["value"], str):
                # IP、操作系统、Agent状态、Agent版本、云区域 单模糊搜索
                custom = condition["value"]
                wheres, sql_params = cls.fuzzy_cond(custom, wheres, sql_params)

            elif condition["key"] == "query" and isinstance(condition["value"], list):
                # IP、操作系统、Agent状态、Agent版本、云区域 多模糊搜索
                for custom in condition["value"]:
                    where_or, sql_params = cls.fuzzy_cond(custom, where_or, sql_params)

        if all([plugin, not has_conditional, not wheres, not where_or]):
            # 此种情况说明不存在额外搜索
            sql = Host.objects.filter(node_type__in=node_type).filter(**filter_values(kwargs))

            return sql

        wheres = init_wheres + wheres

        if where_or:
            # 用AND连接
            wheres = [" AND ".join(wheres) + " AND (" + " OR ".join(where_or) + ")"]

        # 业务节点直接从db获取
        if all_query_biz:
            cond_host_ids = [] if cond_host_ids is None else cond_host_ids
            cond_host_ids.extend(Host.objects.filter(bk_biz_id__in=all_query_biz).values_list("bk_host_id", flat=True))

        if kwargs["bk_host_id__in"] is None:
            # 用户没有传递bk_host_id，如果同时没有传入topo，取全部(None)，否则取一个有效的id列表
            kwargs["bk_host_id__in"] = list(set(cond_host_ids)) if cond_host_ids is not None else None
        else:
            # 查询条件没有启用topo，此时取用户传的bk_host_id列表
            if cond_host_ids is not None:
                kwargs["bk_host_id__in"] = list(set(cond_host_ids) & set(kwargs["bk_host_id__in"]))

        sql = (
            Host.objects.filter(node_type__in=node_type, bk_biz_id__in=biz_permission)
            .extra(select=select, tables=[ProcessStatus._meta.db_table], where=wheres, params=sql_params)
            .filter(**filter_values(kwargs))
        )

        return sql.filter(bk_host_id__in=bk_host_id_list) if plugin and has_conditional else sql

    @staticmethod
    def multiple_cond_sql_running_number(queryset):
        """
        返回通过multiple_cond_sql后得到的queryset的数量
        :param queryset: queryset 表达式
        :return: 运行机器的数量
        """
        return queryset.extra(
            select={"status": f"{JobTask._meta.db_table}.status"},
            tables=[JobTask._meta.db_table],
            where=[
                f"{Host._meta.db_table}.bk_host_id={JobTask._meta.db_table}.bk_host_id",
                f'{JobTask._meta.db_table}.status="{const.StatusType.RUNNING}"',
            ],
        ).count()

    def list(self, params: dict, username: str):
        """
        查询主机
        :param params: 经校验后的数据
        :param username: 用户名数据
        """

        # 用户有权限获取的业务
        # 格式 { bk_biz_id: bk_biz_name , ...}
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.agent_view})

        # 用户主机操作权限
        agent_operate_bizs = CmdbHandler().biz_id_name({"action": IamActionType.agent_operate})

        # 用户没有操作权限的业务
        no_operate_permission = {biz: user_biz[biz] for biz in user_biz if biz not in agent_operate_bizs}

        # 页面
        if params["pagesize"] != -1:
            # 如果是正常数量
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
        else:
            # 跨页全选
            begin = None
            end = None
            # 跨页全选模式，仅返回用户有权限操作的主机
            user_biz = agent_operate_bizs

        if params.get("running_count"):
            # 运行数量统计
            return {
                "running_count": self.multiple_cond_sql_running_number(self.multiple_cond_sql(params, user_biz)),
                "no_permission_count": self.multiple_cond_sql(params, no_operate_permission).count(),
            }

        # 查询
        hosts_status_sql = self.multiple_cond_sql(params, user_biz).exclude(
            bk_host_id__in=params.get("exclude_hosts", [])
        )

        # 计算总数
        hosts_status_count = hosts_status_sql.count()

        if params["only_ip"] is False:
            # sql分页查询获得数据
            hosts_status = list(
                hosts_status_sql[begin:end].values(
                    "bk_cloud_id",
                    "bk_biz_id",
                    "bk_host_id",
                    "os_type",
                    "inner_ip",
                    "outer_ip",
                    "ap_id",
                    "install_channel_id",
                    "login_ip",
                    "data_ip",
                    "status",
                    "version",
                    "created_at",
                    "updated_at",
                    "is_manual",
                    "extra_data",
                )
            )
        else:
            # 如果仅需要IP数据
            hosts_status = [host["inner_ip"] for host in list(hosts_status_sql[begin:end].values("inner_ip"))]
            result = {"total": hosts_status_count, "list": hosts_status}
            return result

        # 分页结果的Host_id, cloud_id集合
        bk_hosts_id = [hs["bk_host_id"] for hs in hosts_status]
        bk_clouds_id = [hs["bk_cloud_id"] for hs in hosts_status]

        # 获得云区域名称
        cloud_name = dict(
            Cloud.objects.filter(bk_cloud_id__in=bk_clouds_id).values_list("bk_cloud_id", "bk_cloud_name")
        )
        cloud_name[0] = DEFAULT_CLOUD_NAME

        # 获得安装通道名称
        install_name_dict = dict(InstallChannel.objects.values_list("id", "name"))

        # 如果需要job result数据
        host_id_job_status = {}
        if "job_result" in params.get("extra_data", []):
            job_status = JobTask.objects.filter(bk_host_id__in=bk_hosts_id).values(
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

        # 如果需要identity数据
        host_id_identities = {}
        if "identity_info" in params.get("extra_data", []):
            # 获得主机信息
            identities = IdentityData.objects.filter(bk_host_id__in=bk_hosts_id).values(
                "bk_host_id", "account", "auth_type", "port", "password", "key"
            )

            host_id_identities = {
                identity["bk_host_id"]: {
                    "account": identity["account"],
                    "auth_type": identity["auth_type"],
                    "port": identity["port"],
                    "re_certification": (
                        False
                        if identity.get("password")
                        or identity.get("key")
                        or identity["auth_type"] == const.AuthType.TJJ_PASSWORD
                        else True
                    ),
                }
                for identity in identities
            }

        # 获得{biz:[bk_host_id]}格式数据
        biz_host_id_map = {}
        for hs in hosts_status:
            if hs["bk_biz_id"] not in biz_host_id_map:
                biz_host_id_map[hs["bk_biz_id"]] = [hs["bk_host_id"]]
            else:
                biz_host_id_map[hs["bk_biz_id"]].append(hs["bk_host_id"])

        # 获得拓扑结构数据
        topology = CmdbHandler().cmdb_or_cache_topo(username, user_biz, biz_host_id_map)

        # 汇总
        for hs in hosts_status:
            hs["status_display"] = const.PROC_STATUS_CHN.get(hs["status"], "")
            hs["bk_cloud_name"] = cloud_name.get(hs["bk_cloud_id"])
            hs["install_channel_name"] = install_name_dict.get(hs["install_channel_id"])
            hs["bk_biz_name"] = user_biz.get(hs["bk_biz_id"], "")
            hs["identity_info"] = host_id_identities.get(hs["bk_host_id"], {})
            hs["job_result"] = host_id_job_status.get(hs["bk_host_id"], {})
            hs["topology"] = topology.get(hs["bk_host_id"], [])
            hs["operate_permission"] = hs["bk_biz_id"] in agent_operate_bizs

        result = {"total": hosts_status_count, "list": hosts_status}

        return result

    def proxies(self, params: dict, username: str, is_superuser: bool):
        """
        查询云区域的proxy列表
        :param params: 经校验后的数据
        :param username: 用户名
        :param is_superuser: 是否超管
        """

        # 用户有权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.proxy_operate})
        all_biz = CmdbHandler().biz_id_name_without_permission()

        # 检测是否有该云区域权限
        CloudHandler().check_cloud_permission(params["bk_cloud_id"], username, is_superuser)

        # 获得proxy相应数据
        proxies = list(
            Host.objects.filter(bk_cloud_id=params["bk_cloud_id"], node_type=const.NodeType.PROXY).values(
                "bk_cloud_id",
                "bk_host_id",
                "inner_ip",
                "outer_ip",
                "login_ip",
                "data_ip",
                "bk_biz_id",
                "is_manual",
                "extra_data",
            )
        )
        bk_host_id_list = [proxy["bk_host_id"] for proxy in proxies]

        # 获得使用proxy的PAGENT个数
        pagent_upstream_nodes = {}
        host_pagent = Host.objects.filter(node_type=const.NodeType.PAGENT, bk_cloud_id=params["bk_cloud_id"]).values(
            "upstream_nodes"
        )
        for nodes in host_pagent:
            for ip in nodes["upstream_nodes"]:
                if ip in pagent_upstream_nodes:
                    pagent_upstream_nodes[ip] += 1
                else:
                    pagent_upstream_nodes[ip] = 1

        # 获得进程状态
        statuses = ProcessStatus.objects.filter(proc_type=const.ProcType.AGENT, bk_host_id__in=bk_host_id_list).values(
            "bk_host_id", "status", "version"
        )

        host_id_status = {
            status["bk_host_id"]: {"status": status["status"], "version": status["version"]} for status in statuses
        }

        # 获得主机信息
        identities = IdentityData.objects.filter(bk_host_id__in=bk_host_id_list).values(
            "bk_host_id", "account", "auth_type", "port", "password", "key"
        )
        host_id_identities = {
            status["bk_host_id"]: {
                "account": status["account"],
                "auth_type": status["auth_type"],
                "port": status["port"],
                "re_certification": False if (status.get("password") or status.get("key")) else True,
            }
            for status in identities
        }

        # job result数据
        job_status = JobTask.objects.filter(bk_host_id__in=bk_host_id_list).values(
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

        # 获得接入点ID
        hosts = dict(Host.objects.filter(bk_host_id__in=bk_host_id_list).values_list("bk_host_id", "ap_id"))

        # 获得接入点名称
        ap_name = APHandler().ap_list(list(hosts.values()))
        ap_name[-1] = "自动选择接入点"

        for proxy in proxies:
            proxy["bk_biz_name"] = all_biz.get(proxy["bk_biz_id"])
            proxy["ap_id"] = hosts.get(proxy["bk_host_id"], 0)
            proxy["ap_name"] = ap_name.get(proxy["ap_id"], "")
            proxy["status"] = host_id_status.get(proxy["bk_host_id"], {}).get("status", "")
            proxy["status_display"] = const.PROC_STATUS_CHN.get(proxy["status"], "")
            proxy["version"] = host_id_status.get(proxy["bk_host_id"], {}).get("version", "")
            proxy["account"] = host_id_identities.get(proxy["bk_host_id"], {}).get("account", "")
            proxy["auth_type"] = host_id_identities.get(proxy["bk_host_id"], {}).get("auth_type", "")
            proxy["port"] = host_id_identities.get(proxy["bk_host_id"], {}).get("port", "")
            proxy["re_certification"] = host_id_identities.get(proxy["bk_host_id"], {}).get("re_certification", "")
            proxy["job_result"] = host_id_job_status.get(proxy["bk_host_id"], {})
            proxy["pagent_count"] = pagent_upstream_nodes.get(proxy["inner_ip"], 0)
            proxy["permissions"] = {"operate": proxy["bk_biz_id"] in user_biz}

        return proxies

    def biz_proxies(self, params: dict, username: str, is_superuser: bool):
        """
        查询业务下云区域的proxy列表
        :param params: 经校验后的数据
        :param username: 用户名
        :param is_superuser: 是否超管
        """

        bk_biz_id = params["bk_biz_id"]

        # 用户有权限的业务
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.proxy_operate}, username=username)
        if bk_biz_id not in user_biz:
            raise BusinessNotPermissionError(_("不存在该业务权限"))

        bk_cloud_ids = (
            Host.objects.filter(bk_biz_id=bk_biz_id)
            .values_list("bk_cloud_id", flat=True)
            .order_by("bk_cloud_id")
            .distinct()
        )

        # 检测是否有该云区域权限
        for cloud_id in bk_cloud_ids:
            if cloud_id != 0:
                CloudHandler().check_cloud_permission(cloud_id, username, is_superuser)

        # 获得proxy相应数据
        proxies = list(
            Host.objects.filter(bk_cloud_id__in=bk_cloud_ids, node_type=const.NodeType.PROXY).values(
                "bk_cloud_id", "bk_host_id", "inner_ip", "outer_ip", "login_ip", "data_ip", "bk_biz_id"
            )
        )

        return proxies

    def update(self, params: dict, username: str, is_superuser: bool):
        """
        更新host相关信息
        :param params: 经校验后的数据
        :param username: 用户名
        :param is_superuser: 是否超管
        """

        # 获得需要更新到Host上的参数信息
        extra_data = {
            "peer_exchange_switch_for_agent": params.get("peer_exchange_switch_for_agent"),
            "bt_speed_limit": params.get("bt_speed_limit"),
        }
        if params.get("data_path"):
            extra_data.update({"data_path": params["data_path"]})
        kwargs = filter_values(
            {
                "bk_host_id": params.get("bk_host_id"),
                "bk_cloud_id": params.get("bk_cloud_id"),
                "outer_ip": params.get("outer_ip"),
                "login_ip": params.get("login_ip"),
                "data_ip": params.get("data_ip"),
                "ap_id": params.get("ap_id"),
                "extra_data": extra_data,
            }
        )
        # 获得需要更新identity的信息
        identity_kwargs = filter_values(
            {
                "bk_host_id": params.get("bk_host_id"),
                "account": params.get("account"),
                "port": params.get("port"),
                "auth_type": params.get("auth_type"),
                "password": params.get("password"),
                "key": params.get("key"),
            }
        )

        # 检测是否有该云区域权限
        CloudHandler().check_cloud_permission(params["bk_cloud_id"], username, is_superuser)

        # 对数据进行校验
        # 检查：Host ID是否正确
        if not Host.objects.filter(bk_host_id=kwargs["bk_host_id"]).exists():
            raise HostIDNotExists(_("Host ID:{bk_host_id} 不存在").format(bk_host_id=kwargs["bk_host_id"]))

        # 检测业务权限
        user_biz = CmdbHandler().biz_id_name({"action": IamActionType.proxy_operate})
        biz = Host.objects.get(bk_host_id=params["bk_host_id"]).bk_biz_id
        if not user_biz.get(biz):
            raise BusinessNotPermissionError(_("您没有该Proxy的操作权限"))

        # 获得该主机的信息
        the_host = Host.objects.get(bk_host_id=kwargs["bk_host_id"])

        # 检查：外网IP是否已被占用
        if kwargs.get("outer_ip") and the_host.outer_ip != kwargs["outer_ip"]:
            if Host.objects.filter(outer_ip=kwargs["outer_ip"], bk_cloud_id=the_host.bk_cloud_id).exists():
                raise IpInUsedError(_("外网IP：{outer_ip} 已被占用").format(outer_ip=kwargs["outer_ip"]))

        # 检查：登录IP是否已被占用
        if kwargs.get("login_ip") and the_host.login_ip != kwargs["login_ip"]:
            if Host.objects.filter(outer_ip=kwargs["login_ip"], bk_cloud_id=the_host.bk_cloud_id).exists():
                raise IpInUsedError(_("登录IP：{login_ip} 已被占用").format(login_ip=kwargs["login_ip"]))

        # 检查：判断AP_ID是否存在数据库中
        if (
            kwargs.get("ap_id")
            and kwargs.get("ap_id") != const.DEFAULT_AP_ID
            and not AccessPoint.objects.filter(id=kwargs["ap_id"]).exists()
        ):
            raise ApIDNotExistsError(_("Ap_id:{ap_id} 不存在于数据库.").format(ap_id=kwargs["ap_id"]))

        # 如果用户没传登录IP，则默认为外网IP
        if not params.get("login_ip"):
            kwargs["login_ip"] = the_host.outer_ip

        # 获得原有认证信息
        identity_info = {
            identity["bk_host_id"]: {
                "auth_type": identity["auth_type"],
                "retention": identity["retention"],
                "account": identity["account"],
                "password": identity["password"],
                "key": identity["key"],
                "port": identity["port"],
            }
            for identity in IdentityData.objects.filter(bk_host_id=kwargs["bk_host_id"]).values(
                "bk_host_id", "auth_type", "retention", "account", "password", "key", "port"
            )
        }

        # 校验密码部分的修改
        not_modified_host, modified_host, ip_filter_list = update_pwd_validate([identity_kwargs], identity_info, [])

        # 如果存在问题则报错
        if len(ip_filter_list) > 0:
            raise PwdCheckError(ip_filter_list[0]["msg"])

        # 校验通过，以下进行信息修改
        update_propeties = filter_values({"bk_host_outerip": kwargs.get("outer_ip")})
        update_cloud = filter_values({"bk_host_ids": [kwargs["bk_host_id"]], "bk_cloud_id": kwargs.get("bk_cloud_id")})

        # 如果需要更新Host的IP信息
        if (
            update_propeties != {}
            and not Host.objects.filter(
                **filter_values(
                    {"bk_host_id": kwargs.get("bk_host_id"), "outer_ip": update_propeties.get("bk_host_outerip")}
                )
            ).exists()
        ):
            CmdbHandler().cmdb_update_host(kwargs["bk_host_id"], update_propeties)

        # 如果需要更新Host的Cloud信息
        if (
            update_cloud.get("bk_cloud_id")
            and not Host.objects.filter(
                bk_host_id=kwargs.get("bk_host_id"), bk_cloud_id=update_cloud["bk_cloud_id"]
            ).exists()
        ):
            CmdbHandler().cmdb_update_host_cloud(update_cloud)

        # 更新Host信息
        host = Host.objects.get(bk_host_id=kwargs["bk_host_id"])
        host.updated_at = timezone.now()
        for kwarg in kwargs:
            # 修改host[kwarg]为 kwargs[kwarg]
            setattr(host, kwarg, kwargs[kwarg])
        host.save()

        # 如果需要更新identity信息
        if len(modified_host) > 0:
            identity, created = IdentityData.objects.get_or_create(bk_host_id=kwargs["bk_host_id"])
            identity.updated_at = timezone.now()
            for kwarg in identity_kwargs:
                setattr(identity, kwarg, identity_kwargs[kwarg])
            identity.save()

    def remove_host(self, params: dict):
        """
        移除主机
        :param params: 参数列表
        """

        # 用户有权限获取的业务
        # 格式 { bk_biz_id: bk_biz_name , ...}
        if params["is_proxy"]:
            user_biz = CmdbHandler().biz_id_name({"action": IamActionType.proxy_operate})
        else:
            user_biz = CmdbHandler().biz_id_name({"action": IamActionType.agent_operate})

        if params.get("exclude_hosts") is not None:
            # 跨页全选, cond内检测权限
            bk_host_ids = list(
                self.multiple_cond_sql(params, user_biz, proxy=params["is_proxy"])
                .exclude(bk_host_id__in=params.get("exclude_hosts", []))
                .values_list("bk_host_id", flat=True)
            )

        else:
            # 非跨页全选, 检查权限
            permission_host_ids = self.check_hosts_permission(params["bk_host_id"], list(user_biz.keys()))
            diff = set(params["bk_host_id"]) - set(permission_host_ids)
            if diff != set():
                ips = list(Host.objects.filter(bk_host_id__in=list(diff)).values_list("inner_ip", flat=True))
                if ips == []:
                    raise HostNotExists(_("主机 {diff} 不存在").format(diff=diff))
                raise NotHostPermission(_("您没有移除主机 {ips} 的权限").format(ips=ips))
            # 如果不是跨页全选模式
            bk_host_ids = permission_host_ids

        with transaction.atomic():
            Host.objects.filter(bk_host_id__in=bk_host_ids).delete()
            IdentityData.objects.filter(bk_host_id__in=bk_host_ids).delete()
            ProcessStatus.objects.filter(bk_host_id__in=bk_host_ids).delete()

        return {}

    def ip_list(self, ips):
        """
        返回存在ips的所有云区域-IP的列表
        :param ips: IP列表
        :return:
        {
            bk_cloud_id+ip: {
                'bk_host_id': ...,
                'bk_biz_id': ...,
                'node_type': ...,
                'ip_type': ...
            }
        },
        """
        inner_ip_info = {
            f"{host['bk_cloud_id']}-{host['inner_ip']}": {
                "outer_ip": host["outer_ip"],
                "login_ip": host["login_ip"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_biz_id": host["bk_biz_id"],
                "node_type": host["node_type"],
                "bk_host_id": host["bk_host_id"],
            }
            for host in Host.objects.filter(inner_ip__in=ips).values(
                "inner_ip", "outer_ip", "login_ip", "bk_cloud_id", "bk_biz_id", "node_type", "bk_host_id"
            )
        }

        outer_ip_info = {
            f"{host['bk_cloud_id']}-{host['outer_ip']}": {
                "inner_ip": host["inner_ip"],
                "login_ip": host["login_ip"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_biz_id": host["bk_biz_id"],
                "node_type": host["node_type"],
                "bk_host_id": host["bk_host_id"],
            }
            for host in Host.objects.filter(outer_ip__in=ips).values(
                "inner_ip", "outer_ip", "login_ip", "bk_cloud_id", "bk_biz_id", "node_type", "bk_host_id"
            )
        }

        login_ip_info = {
            f"{host['bk_cloud_id']}-{host['login_ip']}": {
                "inner_ip": host["inner_ip"],
                "outer_ip": host["outer_ip"],
                "bk_cloud_id": host["bk_cloud_id"],
                "bk_biz_id": host["bk_biz_id"],
                "node_type": host["node_type"],
                "bk_host_id": host["bk_host_id"],
            }
            for host in Host.objects.filter(login_ip__in=ips).values(
                "inner_ip", "outer_ip", "login_ip", "bk_cloud_id", "bk_biz_id", "node_type", "bk_host_id"
            )
        }

        exists_ip_info = {}
        exists_ip_info.update(inner_ip_info)
        exists_ip_info.update(outer_ip_info)
        exists_ip_info.update(login_ip_info)

        return exists_ip_info
