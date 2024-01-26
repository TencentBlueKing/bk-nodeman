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
from typing import Any, Dict, Iterable, List, Set

from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.core.ipchooser import core_ipchooser_constants
from apps.core.ipchooser.tools.base import HostQuerySqlHelper
from apps.core.ipchooser.tools.host_tool import HostTool
from apps.node_man import constants as const
from apps.node_man.constants import IamActionType
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    HostIDNotExists,
    IpInUsedError,
    PwdCheckError,
)
from apps.node_man.handlers.ap import APHandler
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.validator import update_pwd_validate
from apps.node_man.models import (
    AccessPoint,
    Cloud,
    Host,
    IdentityData,
    InstallChannel,
    JobTask,
    ProcessStatus,
)
from apps.node_man.tools.host import HostTools
from apps.utils import APIModel
from apps.utils.basic import filter_values


class HostHandler(APIModel):
    """
    Host处理器
    """

    @staticmethod
    def check_hosts_permission(bk_host_ids: List, permission_biz_ids: List):
        """
        在步骤开始前检查权限
        :param bk_host_ids: 主机ID
        :param permission_biz_ids: 用户有权限的业务ID
        :return permission_host_ids: 有权限的主机ID
        """
        hosts = Host.objects.filter(bk_host_id__in=bk_host_ids).values(
            "bk_host_id", "bk_biz_id", "inner_ip", "bk_cloud_id"
        )
        return [host["bk_host_id"] for host in hosts if host["bk_biz_id"] in permission_biz_ids]

    @classmethod
    def fuzzy_cond(cls, custom: str, wheres: List, sql_params: List):
        """
        用于生成模糊搜索的条件
        :param custom: 用户的输入
        :param wheres: Where 语句列表
        :param sql_params: escape 参数列表
        :return: where, sql_params
        """
        search_sql = f"{Host._meta.db_table}.inner_ip like %s"

        sql_params.extend([f"%{custom}%"])

        # 管控区域搜索
        bk_cloud_names = CloudHandler().list_cloud_name()
        cloud_ids = [str(cloud) for cloud in bk_cloud_names if bk_cloud_names[cloud].find(custom) != -1]
        cloud_ids = ",".join(cloud_ids)
        # 如果存在管控区域结果
        if cloud_ids:
            search_sql += f" OR {Host._meta.db_table}.bk_cloud_id in (%s)"
            sql_params.append(cloud_ids)

        wheres.append("(" + search_sql + ")")
        return wheres, sql_params

    @staticmethod
    def multiple_cond_sql_manual_statistics(queryset):
        """
        返回通过 multiple_cond_sql 后得到的安装方式统计
        :param queryset:
        :return:
        """
        return dict(queryset.values_list("is_manual").order_by("is_manual").annotate(count=Count("is_manual")))

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

        hosts_queryset = HostQuerySqlHelper.multiple_cond_sql(params=params, biz_scope=user_biz.keys())

        if params.get("running_count"):
            # 运行数量统计
            return {
                # TODO 2022Q2 ipc-废弃逻辑移除
                "running_count": 0,
                "no_permission_count": HostQuerySqlHelper.multiple_cond_sql(
                    params=params, biz_scope=no_operate_permission
                ).count(),
                "manual_statistics": self.multiple_cond_sql_manual_statistics(hosts_queryset),
            }

        # 查询
        hosts_status_sql = hosts_queryset.exclude(bk_host_id__in=params.get("exclude_hosts", []))

        # 计算总数
        hosts_status_count = hosts_status_sql.count()

        if params.get("cloud_id_ip"):
            result = HostTools.export_all_cloud_area_colon_ip(params["cloud_id_ip"], hosts_status_sql)
            return {"total": len(result), "list": result}

        if params["only_ip"] is False:
            host_fields = core_ipchooser_constants.CommonEnum.DEFAULT_HOST_FIELDS.value + [
                "bk_addressing",
                "outer_ip",
                "outer_ipv6",
                "ap_id",
                "install_channel_id",
                "login_ip",
                "data_ip",
                "version",
                "created_at",
                "updated_at",
                "is_manual",
                "extra_data",
            ]
            # sql分页查询获得数据
            hosts_status = list(hosts_status_sql[begin:end].values(*set(host_fields)))
        else:
            # 仅需某一列的数据
            value_list = list(filter(None, hosts_status_sql[begin:end].values_list(params["return_field"], flat=True)))
            return {"total": len(value_list), "list": value_list}

        # 分页结果的Host_id, cloud_id集合
        bk_host_ids: List[int] = [hs["bk_host_id"] for hs in hosts_status]
        bk_cloud_ids: List[int] = [hs["bk_cloud_id"] for hs in hosts_status]

        # 获得管控区域名称
        cloud_name = dict(
            Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values_list("bk_cloud_id", "bk_cloud_name")
        )
        cloud_name[0] = str(const.DEFAULT_CLOUD_NAME)

        # 获得安装通道名称
        install_name_dict = dict(InstallChannel.objects.values_list("id", "name"))

        # 如果需要job result数据
        host_id_job_status = {}
        if "job_result" in params.get("extra_data", []):
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

        # 如果需要identity数据
        host_id_identities = {}
        if "identity_info" in params.get("extra_data", []):
            # 获得主机信息
            identities = IdentityData.objects.filter(bk_host_id__in=bk_host_ids).values(
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

        # 实时查询主机状态
        HostTool.fill_agent_state_info_to_hosts(host_infos=hosts_status)

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

    @staticmethod
    def proxies(bk_cloud_id: int):
        """
        查询管控区域的proxy列表
        :param bk_cloud_id: 管控区域ID
        """
        all_biz = CmdbHandler().biz_id_name_without_permission()

        # 获得proxy相应数据
        proxies = list(
            Host.objects.filter(bk_cloud_id=bk_cloud_id, node_type=const.NodeType.PROXY).values(
                "bk_cloud_id",
                "bk_host_id",
                "inner_ip",
                "inner_ipv6",
                "outer_ip",
                "outer_ipv6",
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
        host_pagent = Host.objects.filter(node_type=const.NodeType.PAGENT, bk_cloud_id=bk_cloud_id).values(
            "upstream_nodes"
        )
        for nodes in host_pagent:
            for ip in nodes["upstream_nodes"]:
                if ip in pagent_upstream_nodes:
                    pagent_upstream_nodes[ip] += 1
                else:
                    pagent_upstream_nodes[ip] = 1

        # 获得进程状态
        statuses = ProcessStatus.objects.filter(
            proc_type=const.ProcType.AGENT, name=ProcessStatus.GSE_AGENT_PROCESS_NAME, bk_host_id__in=bk_host_id_list
        ).values("bk_host_id", "status", "version")

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

        return proxies

    @staticmethod
    def biz_proxies(bk_biz_id: int):
        """
        查询业务下管控区域的proxy列表
        :param bk_biz_id: 业务ID
        """
        bk_cloud_ids = (
            Host.objects.filter(bk_biz_id=bk_biz_id)
            .values_list("bk_cloud_id", flat=True)
            .order_by("bk_cloud_id")
            .distinct()
        )

        # 获得proxy相应数据
        proxies = list(
            Host.objects.filter(bk_cloud_id__in=bk_cloud_ids, node_type=const.NodeType.PROXY).values(
                "bk_cloud_id",
                "bk_addressing",
                "inner_ip",
                "inner_ipv6",
                "outer_ip",
                "outer_ipv6",
                "login_ip",
                "data_ip",
                "bk_biz_id",
            )
        )

        return proxies

    @staticmethod
    def update_proxy_info(params: dict):
        """
        更新host相关信息
        :param params: 经校验后的数据
        """

        # 获得需要更新到Host上的参数信息
        extra_data = {
            "peer_exchange_switch_for_agent": params.get("peer_exchange_switch_for_agent"),
            "bt_speed_limit": params.get("bt_speed_limit"),
            "enable_compression": params.get("enable_compression"),
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

        # 对数据进行校验
        # 检查：Host ID是否正确
        if not Host.objects.filter(bk_host_id=kwargs["bk_host_id"]).exists():
            raise HostIDNotExists(_("Host ID:{bk_host_id} 不存在").format(bk_host_id=kwargs["bk_host_id"]))

        # 获得该主机的信息
        the_host = Host.objects.get(bk_host_id=kwargs["bk_host_id"])

        # 检查：外网IP是否已被占用
        if kwargs.get("outer_ip") and the_host.outer_ip != kwargs["outer_ip"]:
            if Host.objects.filter(outer_ip=kwargs["outer_ip"], bk_cloud_id=the_host.bk_cloud_id).exists():
                raise IpInUsedError(_("外网IP：{outer_ip} 已被占用").format(outer_ip=kwargs["outer_ip"]))

        # 检查：登录IP是否已被占用(排除自身的情况)
        if kwargs.get("login_ip") and the_host.login_ip != kwargs["login_ip"]:
            if (
                Host.objects.filter(outer_ip=kwargs["login_ip"], bk_cloud_id=the_host.bk_cloud_id)
                .exclude(bk_host_id=the_host.bk_host_id)
                .exists()
            ):
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
        update_properties = filter_values({"bk_host_outerip": kwargs.get("outer_ip")})
        update_cloud = filter_values({"bk_host_ids": [kwargs["bk_host_id"]], "bk_cloud_id": kwargs.get("bk_cloud_id")})

        # 如果需要更新Host的IP信息
        if (
            update_properties != {}
            and not Host.objects.filter(
                **filter_values(
                    {"bk_host_id": kwargs.get("bk_host_id"), "outer_ip": update_properties.get("bk_host_outerip")}
                )
            ).exists()
        ):
            CmdbHandler().cmdb_update_host(kwargs["bk_host_id"], update_properties)

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

        # 更新ProcessStatus中Proxy包版本信息
        if params.get("version"):
            ProcessStatus.objects.filter(bk_host_id=kwargs["bk_host_id"]).update(version=params["version"])

    @staticmethod
    def get_host_infos_gby_ip_key(ips: Iterable[str], ip_version: int):
        """
        获取 主机信息根据 IP 等关键信息聚合的结果
        :param ips:
        :param ip_version:
        :return:
        """

        if not ips:
            return {}

        ips: Set[str] = set(ips)
        login_ip_field_name: str = "login_ip"
        login_ip_filter_k: str = "login_ip__in"

        # 根据 IP 版本筛选不同的 IP 字段
        if ip_version == const.CmdbIpVersion.V6.value:
            inner_ip_field_name = "inner_ipv6"
            outer_ip_field_name = "outer_ipv6"
            inner_ip_filter_k = "inner_ipv6__in"
            outer_ip_filter_k = "outer_ipv6__in"
        else:
            inner_ip_field_name = "inner_ip"
            outer_ip_field_name = "outer_ip"
            inner_ip_filter_k = "inner_ip__in"
            outer_ip_filter_k = "outer_ip__in"

        fields: List[str] = [
            "inner_ip",
            "inner_ipv6",
            "bk_agent_id",
            "outer_ip",
            "outer_ipv6",
            "login_ip",
            "bk_cloud_id",
            "bk_biz_id",
            "node_type",
            "bk_host_id",
            "bk_addressing",
            "ap_id",
        ]
        host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for host_info in Host.objects.filter(
            Q(**{inner_ip_filter_k: ips}) | Q(**{outer_ip_filter_k: ips}) | Q(**{login_ip_filter_k: ips})
        ).values(*fields):
            ip_filed_names: List[str] = [inner_ip_field_name, login_ip_field_name, outer_ip_field_name]
            for ip_filed_name in ip_filed_names:
                # 不满足 < IP 不为空 且 IP 存在于 IP 列表 > 时，提前结束处理逻辑
                if not (host_info[ip_filed_name] and host_info[ip_filed_name] in ips):
                    continue
                ip_key: str = f"{host_info['bk_addressing']}:{host_info['bk_cloud_id']}:{host_info[ip_filed_name]}"
                host_infos_gby_ip_key[ip_key].append(host_info)
        return host_infos_gby_ip_key
