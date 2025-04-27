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
import typing
from collections import defaultdict

from django.conf import settings
from django.db.models.aggregates import Count
from django.utils.translation import ugettext_lazy as _

from apps.adapters.api.gse import get_gse_api_helper
from apps.backend.components.collections.base import DBHelperMixin
from apps.node_man import constants as const
from apps.node_man import models, tools
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    CloudNotExistError,
    NotExistsOs,
    ProxyNotAvaliableError,
)
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.models import AccessPoint, Host, IdentityData, ProcessStatus


def check_available_proxy():
    """
    获得有可用代理的管控区域
    :return:
    {
        bk_cloud_id: True,
    },
    {
        bk_cloud_id: 1,
    }
    """

    check_result = {}

    # 获得所有代理的信息
    proxies = Host.objects.filter(node_type=const.NodeType.PROXY).values(
        "bk_host_id", "bk_biz_id", "bk_cloud_id", "is_manual"
    )
    proxies_info = {
        proxy["bk_host_id"]: {
            "bk_biz_id": proxy["bk_biz_id"],
            "bk_cloud_id": proxy["bk_cloud_id"],
            "is_manual": proxy["is_manual"],
        }
        for proxy in proxies
    }

    # 获得所有代理的状态
    process_status = dict(
        ProcessStatus.objects.filter(bk_host_id__in=list(proxies_info.keys()), name="gseagent").values_list(
            "bk_host_id", "status"
        )
    )

    # 获得所有代理的认证信息
    identity_info = {
        identity["bk_host_id"]: {
            "auth_type": identity["auth_type"],
            "retention": identity["retention"],
            "account": identity["account"],
            "password": identity["password"],
            "key": identity["key"],
            "port": identity["port"],
            "extra_data": identity["extra_data"],
        }
        for identity in IdentityData.objects.filter(bk_host_id__in=list(proxies_info.keys())).values(
            "bk_host_id",
            "auth_type",
            "retention",
            "account",
            "password",
            "key",
            "port",
            "extra_data",
        )
    }

    # 标记管控区域中是否有可用Proxy
    for host_id in proxies_info:
        proxy_cloud_id = proxies_info[host_id]["bk_cloud_id"]
        if identity_info.get(host_id) and (proxy_cloud_id not in check_result or not check_result[proxy_cloud_id]):
            if process_status.get(host_id) == "RUNNING" and (
                identity_info[host_id].get("key")
                or identity_info[host_id].get("password")
                or proxies_info[host_id]["is_manual"]
            ):
                check_result[proxy_cloud_id] = True

    # 每个管控区域下的代理数量
    # 获得相同bk_cloud_id的Proxy个数
    proxies_count = dict(
        Host.objects.filter(node_type=const.NodeType.PROXY)
        .values_list("bk_cloud_id")
        .annotate(node_count=Count("bk_cloud_id"))
        .order_by()
    )

    return check_result, proxies_count


def bulk_update_validate(
    host_info: dict,
    accept_list: list,
    identity_info: dict,
    ip_filter_list: list,
    is_manual: bool = False,
):
    """
    用于批量修改时的数据校验
    :param host_info: 数据库Host列表
    :param accept_list: 所有Host列表
    :param identity_info: 所有认证信息
    :param ip_filter_list: 过滤掉的Ip
    :param is_manual: 是否手动安装

    :return
    {
        #需要更新认证信息的Host
        'modified_host': modified_host
        #不需要更新认证信息的Host
        'not_modified_host': not_modified_host
        #不需要修改主机信息的Host
        'not_modified_host': not_modified_host
        #需要修改主机信息的Host
        'modified_host': modified_host
        #被过滤的IP列表
        'ip_filter_list': ip_filter_list
        #订阅任务所需要的id
        'subscription_host_ids': subscription_host_ids
    }
    """

    not_modified_identity = []
    modified_identity = []

    # 认证信息校验器
    if not is_manual:
        not_modified_identity, modified_identity, ip_filter_list = update_pwd_validate(
            accept_list, identity_info, ip_filter_list
        )

    # 检测host需不需要进行修改
    not_modified_host = []
    modified_host = []
    for host in accept_list:
        # 系统变更/接入点变更/DHT变更需要更新主机
        host_extra_data = host_info[host["bk_host_id"]]["extra_data"] or {}

        if (
            host.get("os_type") != host_info[host["bk_host_id"]]["os_type"]
            or (host.get("ap_id") != host_info[host["bk_host_id"]]["ap_id"] and not host.get("is_need_inject_ap_id"))
            or host.get("bt_speed_limit") != host_extra_data.get("bt_speed_limit")
            or host.get("peer_exchange_switch_for_agent") != host_extra_data.get("peer_exchange_switch_for_agent")
            or host.get("enable_compression") != host_extra_data.get("enable_compression")
            or host.get("login_ip") != host_info[host["bk_host_id"]]["login_ip"]
            or host.get("data_path") != host_extra_data.get("data_path")
            or host.get("install_channel_id") != host_info[host["bk_host_id"]]["install_channel_id"]
        ):
            modified_host.append(host)
        else:
            not_modified_host.append(host)

    subscription_host_ids = []
    filter_host_ids = {host["bk_host_id"] for host in ip_filter_list}

    for host in modified_host + not_modified_host:
        if host["bk_host_id"] in filter_host_ids:
            continue
        # bk_cloud_id & install_channel_id 用于快速识别一台机器是否为跨云机器
        subscription_host_ids.append(
            {
                "bk_host_id": host["bk_host_id"],
                "bk_cloud_id": host["bk_cloud_id"],
                "ap_id": host["ap_id"],
                "install_channel_id": host.get("install_channel_id"),
                "is_need_inject_ap_id": host.get("is_need_inject_ap_id"),
            }
        )

    return (
        {
            "not_modified_identity": not_modified_identity,
            "modified_identity": modified_identity,
            "not_modified_host": not_modified_host,
            "modified_host": modified_host,
            "subscription_host_ids": subscription_host_ids,
        },
        ip_filter_list,
    )


def update_pwd_validate(accept_list: list, identity_info: dict, ip_filter_list: list):
    """
    用于修改时，认证信息的密码部分校验
    :param accept_list: 所有Host列表
    :param identity_info: 所有认证信息
    :param ip_filter_list: 过滤掉的Ip
    :return
    (
        modified_host: 需要更新认证信息的host
        not_modified_host: 不需要更新认证信息的host
        ip_filter_list: 被过滤的IP列表
    )
    """
    not_modified_host = []
    modified_host = []

    for host in accept_list:

        # 过滤主机
        error_host = {
            "ip": host.get("inner_ip"),
            "bk_host_id": host.get("bk_host_id"),
            "bk_cloud_name": "",
            "bk_biz_name": "",
            "job_id": "",
            "msg": "",
        }

        # 验证类型等于铁将军类型无条件更新
        if host.get("auth_type") == const.AuthType.TJJ_PASSWORD:
            modified_host.append(host)

        # 如果用户修改了认证类型，但是没上传相应的密码或key，返回相应的错误
        elif host.get("auth_type") and host.get("auth_type") != identity_info.get(host["bk_host_id"], {}).get(
            "auth_type"
        ):

            if host.get("auth_type") == const.AuthType.KEY and not host.get("key"):
                error_host["msg"] = _("修改了认证类型为秘钥认证，但是没有输入认证凭证")
                ip_filter_list.append(error_host)

            elif host.get("auth_type") == const.AuthType.PASSWORD and not host.get("password"):
                error_host["msg"] = _("修改了认证类型为密码认证，但是没有输入密码")
                ip_filter_list.append(error_host)

            else:
                modified_host.append(host)

        # 认证信息过期：如果用户没上传密码或key，且数据库中密码和key皆为空值
        elif (
            not host.get("password")
            and not host.get("key")
            and not identity_info.get(host["bk_host_id"]).get("password")
            and not identity_info.get(host["bk_host_id"]).get("key")
        ):
            error_host["msg"] = _("认证信息已过期，请输入相关认证信息")
            ip_filter_list.append(error_host)

        # 如果用户没上传密码、秘钥、且端口、账号没有发生变化，不进行修改操作
        elif (
            not host.get("password")
            and not host.get("key")
            and host.get("port") == identity_info.get(host["bk_host_id"]).get("port")
            and host.get("account") == identity_info.get(host["bk_host_id"]).get("account")
        ):
            not_modified_host.append(host)
        else:
            # 否则需要修改
            modified_host.append(host)

    return not_modified_host, modified_host, ip_filter_list


def new_install_ip_checker(
    host_infos_gby_ip_key: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]],
    host_info: typing.Dict[str, typing.Any],
    error_host: typing.Dict[str, typing.Dict],
    biz_info: typing.Dict[str, typing.Any],
    bk_cloud_info: typing.Dict[str, typing.Any],
    biz_id__biz_name_map: typing.Dict[int, str],
    host_id__agent_state_info_map: typing.Dict[int, typing.Dict[str, typing.Any]],
) -> bool:
    """
    新装校验
    :param host_infos_gby_ip_key: 主机信息根据 IP 等关键信息聚合的结果
    :param host_info: 主机信息
    :param error_host: 错误信息
    :param biz_info: 期望安装到的目标业务信息
    :param bk_cloud_info: 期望安装到的管控区域信息
    :param biz_id__biz_name_map: 主机 ID - 主机名称 映射
    :param host_id__agent_state_info_map: 主机 ID - Agent 进程信息映射关系
    :return:
    """
    host_infos_with_the_same_ips: typing.List[
        typing.Dict[str, typing.Any]
    ] = tools.HostV2Tools.get_host_infos_with_the_same_ips(
        host_infos_gby_ip_key=host_infos_gby_ip_key, host_info=host_info, ip_field_names=["inner_ip", "inner_ipv6"]
    )

    if not host_infos_with_the_same_ips:
        return True

    # 动态 IP 或者 IP 不存在的情况下允许新增
    if host_info["bk_addressing"] == const.CmdbAddressingType.DYNAMIC.value:
        # 动态场景下的主机存在性校验
        # 1. Agent 状态存活，提示去重装
        # 2. Agent 已经失联，新增
        first_online_host: typing.Optional[typing.Dict] = None
        for host_info_with_the_same_ip in host_infos_with_the_same_ips:
            is_running: bool = (
                host_id__agent_state_info_map.get(host_info_with_the_same_ip["bk_host_id"], {}).get("bk_agent_alive")
                == const.BkAgentStatus.ALIVE.value
            )

            if is_running:
                first_online_host = host_info_with_the_same_ip
                break

        # Agent 已经失联，允许新增
        if first_online_host is None:
            # 如果存在其他同 IP + 管控区域失联的 Agent，声明本次安装需要重新生成 AgentID
            if host_infos_with_the_same_ips:
                host_info["force_update_agent_id"] = True
            return True
        else:
            error_host["msg"] = _(
                "已有 Agent 存活的动态寻址主机【bk_host_id: {bk_host_id}】位于所选「管控区域」：{bk_cloud_name}，业务：{bk_biz_name}"
            ).format(
                bk_host_id=first_online_host["bk_host_id"],
                ipv4=first_online_host["inner_ip"],
                ipv6=first_online_host["inner_ipv6"],
                bk_cloud_name=bk_cloud_info.get("bk_cloud_name") or "",
                bk_biz_name=biz_id__biz_name_map.get(first_online_host["bk_biz_id"], first_online_host["bk_biz_id"]),
            )
            return False

    # 静态 IP 信息已存在，有且仅存在一个
    exist_host_info: typing.Dict[str, typing.Any] = host_infos_with_the_same_ips[0]

    # 当业务一致时，视为重装
    # 当业务不一致时，校验失败，提示该主机已安装到其他业务下
    if exist_host_info["bk_biz_id"] != host_info["bk_biz_id"]:
        # 已被占用则跳过并记录
        error_host["msg"] = _(
            """
            该主机内网IP已存在于所选「管控区域」：{bk_cloud_name} 下,
            业务：{bk_biz_name},
            节点类型：{node_type}
            """
        ).format(
            bk_cloud_name=bk_cloud_info.get("bk_cloud_name") or "",
            bk_biz_name=biz_id__biz_name_map.get(exist_host_info["bk_biz_id"], exist_host_info["bk_biz_id"]),
            node_type=exist_host_info["node_type"],
        )
        return False

    inner_ipv4: typing.Optional[str] = host_info.get("inner_ip")
    inner_ipv6: typing.Optional[str] = host_info.get("inner_ipv6")
    # 如果 ipv4 / ipv6 同时存在，也必须是绑定关系
    if inner_ipv4 and inner_ipv6 and exist_host_info["inner_ipv6"] and exist_host_info["inner_ipv6"] != inner_ipv6:
        error_host["msg"] = _(
            "该主机(bk_host_id:{bk_host_id}) 已存在且 IP 信息为：IPv4({ipv4}), IPv6({ipv6})，"
            "不允许修改为 IPv4({ipv4}), IPv6({to_be_add_ipv6})"
        ).format(
            bk_host_id=exist_host_info["bk_host_id"],
            ipv4=inner_ipv4,
            ipv6=exist_host_info["inner_ipv6"],
            to_be_add_ipv6=inner_ipv6,
        )
        return False
    return True


def operate_ip_checker(
    host_infos_gby_ip_key: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]],
    host_info: typing.Dict[str, typing.Any],
    error_host: typing.Dict[str, typing.Dict],
    op_type: str,
    node_type: str,
):

    host_infos_with_the_same_ips: typing.List[
        typing.Dict[str, typing.Any]
    ] = tools.HostV2Tools.get_host_infos_with_the_same_ips(
        host_infos_gby_ip_key=host_infos_gby_ip_key, host_info=host_info, ip_field_names=["inner_ip", "inner_ipv6"]
    )

    if not host_infos_with_the_same_ips:
        error_host["msg"] = _("尚未被安装，无法执行 {op_type} 操作").format(op_type=const.JOB_TYPE_DICT[op_type + "_" + node_type])
        return False

    host_info_with_the_same_host_id: typing.Optional[typing.Dict[str, typing.Any]] = None
    for host_info_with_the_same_ips in host_infos_with_the_same_ips:
        if host_info_with_the_same_ips["bk_host_id"] == host_info["bk_host_id"]:
            host_info_with_the_same_host_id = host_info_with_the_same_ips
            break

    if host_info_with_the_same_host_id is None:
        error_host["msg"] = _("Host ID 不正确，无法执行 {op_type} 操作").format(
            op_type=const.JOB_TYPE_DICT[op_type + "_" + node_type]
        )
        return False

    # 检查：节点类型是否与操作类型一致, 如本身为 PROXY，重装却为 AGENT
    # 此处不区分 P-AGENT 和 AGENT
    if node_type not in host_info_with_the_same_host_id["node_type"]:
        error_host["msg"] = _("节点类型不正确，该主机是 {host_node_type}, 而请求的操作类型是 {node_type}").format(
            host_node_type=host_info_with_the_same_host_id["node_type"], node_type=node_type
        )
        return False

    return True


def install_validate(
    hosts: typing.List[typing.Dict[str, typing.Any]],
    op_type: str,
    node_type: str,
    job_type: str,
    biz_id__biz_name_map: dict,
    cloud_info: dict,
    ap_id_name: dict,
    host_infos_gby_ip_key: dict,
):
    """
    用于job任务的校验
    :param hosts: 主机列表
    :param op_type: 操作类型
    :param node_type: 节点类型
    :param job_type: 任务作业类型
    :param biz_id__biz_name_map: 用户的业务列表
    :param cloud_info: 获得相应管控区域 id, name, ap_id, bk_biz_scope
    :param ap_id_name: 获得接入点列表
    :param host_infos_gby_ip_key: DB中内网IP信息
    :return: 列表，ip被占用及其原因
    """
    accept_list = []
    ip_filter_list = []
    proxy_not_alive = []

    # 获得有可用代理的管控区域
    available_clouds, proxies_count = check_available_proxy()

    if all(
        [
            op_type in [const.OpType.INSTALL, const.OpType.REPLACE],
            job_type != const.JobType.INSTALL_PROXY,
            settings.BKAPP_ENABLE_DHCP,
        ]
    ):

        # 获取接入点映射关系
        ap_id_obj_map = AccessPoint.ap_id_obj_map()

        query_hosts__gby_gse_version: typing.Dict[str, typing.List[typing.Dict[str, typing.Any]]] = defaultdict(list)
        for host_infos in host_infos_gby_ip_key.values():
            for host_info in host_infos:
                gse_version = ap_id_obj_map[host_info["ap_id"]].gse_version
                query_hosts__gby_gse_version[gse_version].append(
                    {
                        "bk_host_id": host_info["bk_host_id"],
                        "ip": host_info["inner_ip"] or host_info["inner_ipv6"],
                        "bk_cloud_id": host_info["bk_cloud_id"],
                        "bk_agent_id": host_info["bk_agent_id"],
                    }
                )

        agent_id__agent_state_info_map: typing.Dict[str, typing.Dict] = defaultdict(dict)
        host_id__agent_state_info_map: typing.Dict[int, typing.Dict] = {}
        for gse_version, query_hosts in query_hosts__gby_gse_version.items():
            gse_api_helper = get_gse_api_helper(ap_id_obj_map[host_info["ap_id"]].gse_version)
            agent_id__agent_state_info_map.update(gse_api_helper.list_agent_state(query_hosts))
            for query_host in query_hosts:
                agent_id: str = gse_api_helper.get_agent_id(query_host)
                host_id__agent_state_info_map[query_host["bk_host_id"]] = agent_id__agent_state_info_map.get(
                    agent_id, {}
                )
    else:
        host_id__agent_state_info_map = {}

    add_host_biz_blacklist = []
    if job_type in [const.JobType.INSTALL_AGENT]:
        add_host_biz_blacklist: typing.List[int] = models.GlobalSettings.get_config(
            models.GlobalSettings.KeyEnum.ADD_HOST_BIZ_BLACKLIST.value, default=[]
        )

    for host in hosts:
        ap_id = host.get("ap_id")
        bk_biz_id = host["bk_biz_id"]
        bk_cloud_id = host["bk_cloud_id"]
        ip = host.get("inner_ip") or host.get("inner_ipv6")

        bk_cloud_info = cloud_info.get(bk_cloud_id, {})
        biz_info = {"bk_biz_id": bk_biz_id, "bk_biz_name": biz_id__biz_name_map.get(bk_biz_id)}
        error_host = {
            **biz_info,
            "ip": ip,
            "inner_ip": host.get("inner_ip"),
            "inner_ipv6": host.get("inner_ipv6"),
            "bk_host_id": host.get("bk_host_id"),
            "bk_cloud_name": bk_cloud_info.get("bk_cloud_name") or "",
            "bk_cloud_id": bk_cloud_id,
            "status": const.JobStatusType.IGNORED,
            "job_id": "",
            "exception": "",
            "msg": "",
        }

        # 检查：bk_biz_id和bk_cloud_id是否在新增主机黑名单
        if all(
            [
                job_type in [const.JobType.INSTALL_AGENT],
                bk_cloud_id in DBHelperMixin().add_host_cloud_blacklist,
                bk_biz_id in add_host_biz_blacklist,
            ]
        ):
            error_host["msg"] = _("管控区域【ID：{bk_cloud_id}】已被管理员限制新增主机").format(bk_cloud_id=bk_cloud_id)
            error_host["exception"] = "limit_add_host"
            ip_filter_list.append(error_host)
            continue

        # 检查：是否有操作系统参数
        if not host.get("os_type") and node_type != const.NodeType.PROXY:
            raise NotExistsOs(_("主机(IP:{ip}) 没有操作系统, 请【重装】并补全相关信息").format(ip=ip))

        # 检查：管控区域是否存在
        if bk_cloud_id != const.DEFAULT_CLOUD and bk_cloud_id not in cloud_info:
            raise CloudNotExistError(_("管控区域(ID:{bk_cloud_id}) 不存在").format(bk_cloud_id=bk_cloud_id))

        # 检查：直连区域不允许安装 PROXY
        if bk_cloud_id == const.DEFAULT_CLOUD and node_type == const.NodeType.PROXY:
            raise ProxyNotAvaliableError(
                _("{bk_cloud_name} 是「直连区域」，不可以安装PROXY").format(bk_cloud_name=bk_cloud_info.get("bk_cloud_name") or "")
            )

        # 检查：判断 P-Agent 情况下代理是否可用
        if (
            bk_cloud_id != const.DEFAULT_CLOUD
            and node_type != const.NodeType.PROXY
            and op_type != const.OpType.RESTART
            and proxies_count.get(host.get("bk_cloud_id"), 0) == 0
        ):
            error_host["msg"] = _("该「管控区域」下不存在代理")
            error_host["exception"] = "no_proxy"
            ip_filter_list.append(error_host)
            proxy_not_alive.append(error_host)
            continue

        # 检查：判断参数AP_ID是否存在
        if bk_cloud_id == const.DEFAULT_CLOUD and not ap_id:
            raise ApIDNotExistsError(_("直连区域必须选择接入点"))

        # 检查：判断AP_ID是否存在数据库中
        if ap_id != const.DEFAULT_AP_ID and ap_id not in ap_id_name:
            raise ApIDNotExistsError(_("接入点(id:{ap_id})不存在").format(ap_id=ap_id))

        is_check_pass = True
        if op_type in [const.OpType.INSTALL, const.OpType.REPLACE] and job_type != const.JobType.INSTALL_PROXY:

            is_check_pass = new_install_ip_checker(
                host_infos_gby_ip_key=host_infos_gby_ip_key,
                host_info=host,
                error_host=error_host,
                biz_info=biz_info,
                bk_cloud_info=bk_cloud_info,
                biz_id__biz_name_map=biz_id__biz_name_map,
                host_id__agent_state_info_map=host_id__agent_state_info_map,
            )

        elif op_type not in [const.OpType.INSTALL, const.OpType.REPLACE]:
            is_check_pass = operate_ip_checker(
                host_infos_gby_ip_key=host_infos_gby_ip_key,
                host_info=host,
                error_host=error_host,
                op_type=op_type,
                node_type=node_type,
            )

        if is_check_pass:
            accept_list.append(dict(host))
        else:
            ip_filter_list.append(error_host)

    return ip_filter_list, accept_list, proxy_not_alive


def operate_validator(db_host_sql, host_info: typing.Dict[int, typing.Dict[str, typing.Any]] = {}):
    """
    用于operate任务的校验
    :param db_host_sql: 用户操作主机的详细信息
    :return: 列表，ip被占用及其原因
    """

    # 可以进入下一步的Host ID
    permission_host_ids = []
    # 获得所有管控区域ID
    bk_cloud_ids = [host["bk_cloud_id"] for host in db_host_sql]
    # 获得所有管控区域信息
    cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

    for host in db_host_sql:
        # 检查：是否有操作系统参数
        if not host.get("os_type") and host["node_type"] != const.NodeType.PROXY:
            raise NotExistsOs(_("主机(IP:{inner_ip}) 没有操作系统, 请【重装】并补全相关信息").format(inner_ip=host["inner_ip"]))

        # 管控区域是否存在
        if not cloud_info.get(host["bk_cloud_id"]):
            raise CloudNotExistError(_("不允许操作【管控区域不存在】的主机,「管控区域」id: {}").format(host["bk_cloud_id"]))

        permission_host_ids.append(host["bk_host_id"])

    # 获得业务ID
    host_biz_scope = list({host["bk_biz_id"] for host in db_host_sql})

    db_hosts: typing.List[typing.Dict[str, typing.Any]] = []

    for host_id in permission_host_ids:
        _host = {"bk_host_id": host_id}
        _host.update(host_info.get(host_id, {}))
        db_hosts.append(_host)

    return db_hosts, host_biz_scope
