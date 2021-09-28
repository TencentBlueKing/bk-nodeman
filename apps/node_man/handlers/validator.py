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
from django.db.models.aggregates import Count
from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants as const
from apps.node_man.constants import IamActionType
from apps.node_man.exceptions import (
    ApIDNotExistsError,
    BusinessNotPermissionError,
    CloudNotExistError,
    CloudNotPermissionError,
    IpRunningJob,
    NotExistsOs,
    ProxyNotAvaliableError,
)
from apps.node_man.handlers.cloud import CloudHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import Host, IdentityData, ProcessStatus
from apps.utils.local import get_request_username


def check_available_proxy():
    """
    获得有可用代理的云区域
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

    # 标记云区域中是否有可用Proxy
    for host_id in proxies_info:
        proxy_cloud_id = proxies_info[host_id]["bk_cloud_id"]
        if identity_info.get(host_id) and (proxy_cloud_id not in check_result or not check_result[proxy_cloud_id]):
            if process_status.get(host_id) == "RUNNING" and (
                identity_info[host_id].get("key")
                or identity_info[host_id].get("password")
                or proxies_info[host_id]["is_manual"]
            ):
                check_result[proxy_cloud_id] = True

    # 每个云区域下的代理数量
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
            or host.get("ap_id") != host_info[host["bk_host_id"]]["ap_id"]
            or host.get("bt_speed_limit") != host_extra_data.get("bt_speed_limit")
            or host.get("peer_exchange_switch_for_agent") != host_extra_data.get("peer_exchange_switch_for_agent")
            or host.get("login_ip") != host_info[host["bk_host_id"]]["login_ip"]
            or host.get("data_path") != host_extra_data.get("data_path")
            or host.get("install_channel_id") != host_info[host["bk_host_id"]]["install_channel_id"]
        ):
            modified_host.append(host)
        else:
            not_modified_host.append(host)

    # 用于订阅任务的bk_host_id，此处要去除密码校验器过滤掉的host
    subscription_host_ids = list(
        {host["bk_host_id"] for host in modified_host + not_modified_host}
        - {host["bk_host_id"] for host in ip_filter_list}
    )

    # 改为用于订阅安装任务的格式
    subscription_host_ids = [{"bk_host_id": host_id} for host_id in subscription_host_ids]

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


def job_validate(
    biz_info: dict,
    data: dict,
    cloud_info: dict,
    ap_id_name: dict,
    inner_ip_info: dict,
    bk_biz_scope: list,
    task_info: dict,
    username: str,
    is_superuser: bool,
    ticket: str,
):
    """
    用于job任务的校验
    :param biz_info: 用户的业务列表
    :param data: 请求参数数据
    :param cloud_info: 获得相应云区域 id, name, ap_id, bk_biz_scope
    :param ap_id_name: 获得接入点列表
    :param inner_ip_info: DB中内网IP信息
    :param bk_biz_scope: Host中的bk_biz_scope列表
    :param task_info: 任务执行信息
    :param username: 用户名
    :param is_superuser: 是否为超管
    :param ticket: 用户ticket，用于后台异步执行时调用第三方接口使用
    :return: 列表，ip被占用及其原因
    """

    op_type = data["op_type"]
    node_type = data["node_type"]

    ip_filter_list = []
    accept_list = []
    proxy_not_alive = []

    # 向权限中心获取用户的云区域权限
    if settings.USE_IAM:
        cloud_view_permission = IamHandler().fetch_policy(get_request_username(), [IamActionType.cloud_view])[
            IamActionType.cloud_view
        ]
    else:
        cloud_view_permission = [cloud for cloud in cloud_info if username in cloud_info[cloud]["creator"]]

    # 获得有可用代理的云区域
    available_clouds, proxies_count = check_available_proxy()

    # 检查：用户是否有操作这些业务的权限
    # TODO: 转移至权限中心
    diff = set(bk_biz_scope) - set(biz_info.keys())
    if diff != set():
        raise BusinessNotPermissionError(_("用户不具有 {diff} 的业务权限").format(diff=diff))

    for host in data["hosts"]:
        host["ticket"] = ticket
        ip = host["inner_ip"]
        bk_cloud_id = host["bk_cloud_id"]
        bk_biz_id = host["bk_biz_id"]
        ap_id = host.get("ap_id")

        # 云区域名称
        cloud_name = cloud_info.get(bk_cloud_id, {}).get("bk_cloud_name", "")
        biz_name = biz_info.get(bk_biz_id)
        error_host = {
            "ip": ip,
            "bk_host_id": host.get("bk_host_id"),
            "bk_cloud_name": cloud_name,
            "bk_biz_name": biz_name,
            "bk_cloud_id": bk_cloud_id,
            "status": const.JobStatusType.IGNORED,
            "job_id": "",
            "exception": "",
            "msg": "",
        }

        # 检查：是否有操作系统参数
        if not host.get("os_type") and node_type != const.NodeType.PROXY:
            raise NotExistsOs(_("主机(IP:{ip}) 没有操作系统, 请【重装】并补全相关信息").format(ip=ip))

        # 检查：云区域是否存在
        if bk_cloud_id != const.DEFAULT_CLOUD and bk_cloud_id not in cloud_info:
            raise CloudNotExistError(_("云区域(ID:{bk_cloud_id}) 不存在").format(bk_cloud_id=bk_cloud_id))

        # 检查：是否有该云区域权限
        if bk_cloud_id != const.DEFAULT_CLOUD and bk_cloud_id not in cloud_view_permission and not is_superuser:
            raise CloudNotPermissionError(
                _("您不具有云区域 {bk_cloud_name} 的权限").format(bk_cloud_name=cloud_info[bk_cloud_id]["bk_cloud_name"])
            )

        # 检查：直连区域不允许安装PROXY
        if bk_cloud_id == const.DEFAULT_CLOUD and node_type == const.NodeType.PROXY:
            raise ProxyNotAvaliableError(_("{cloud_name} 是直连区域，不可以安装PROXY").format(cloud_name=cloud_name))

        # 检查：判断P-Agent情况下代理是否可用
        if (
            bk_cloud_id != const.DEFAULT_CLOUD
            and node_type != const.NodeType.PROXY
            and op_type != const.OpType.RESTART
            and proxies_count.get(host.get("bk_cloud_id"), 0) == 0
        ):
            error_host["msg"] = _("该云区域下不存在代理")
            error_host["exception"] = "no_proxy"
            ip_filter_list.append(error_host)
            proxy_not_alive.append(error_host)
            continue

        # 检查：判断参数AP_ID是否存在
        if bk_cloud_id == const.DEFAULT_CLOUD and not ap_id:
            raise ApIDNotExistsError(_("直连区域必须选择接入点"))

        # 检查：判断非直连区域的接入点是否为其云区域接入点
        if (
            bk_cloud_id != const.DEFAULT_CLOUD
            and cloud_info[bk_cloud_id]["ap_id"] != const.DEFAULT_AP_ID
            and ap_id != cloud_info[bk_cloud_id]["ap_id"]
            and not host["is_manual"]
        ):
            raise ApIDNotExistsError(
                _("接入点参数与所属云区域({bk_cloud_name})的接入点不对应").format(bk_cloud_name=cloud_info[bk_cloud_id]["bk_cloud_name"])
            )

        # 检查：判断AP_ID是否存在数据库中
        if ap_id != const.DEFAULT_AP_ID and ap_id not in ap_id_name:
            raise ApIDNotExistsError(_("接入点(id:{ap_id})不存在").format(ap_id=ap_id))

        # 检查：判断内网ip是否已被占用
        cloud_inner_ip = str(bk_cloud_id) + "-" + ip
        if (
            op_type in [const.OpType.INSTALL, const.OpType.REPLACE]
            and cloud_inner_ip in inner_ip_info
            and data["job_type"] != const.JobType.INSTALL_PROXY  # 这里允许把Agent安装为proxy，因此不做IP冲突检查
        ):
            # 已被占用则跳过并记录
            error_host["msg"] = _(
                """
                该主机内网IP已存在于所选云区域：{cloud_name} 下,
                业务：{bk_biz_id},
                节点类型：{node_type}
                """
            ).format(
                cloud_name=cloud_name,
                bk_biz_id=biz_info.get(
                    inner_ip_info[cloud_inner_ip]["bk_biz_id"], inner_ip_info[cloud_inner_ip]["bk_biz_id"]
                ),
                node_type=inner_ip_info[cloud_inner_ip]["node_type"],
            )
            ip_filter_list.append(error_host)
            continue

        # 非新装任务校验
        if op_type not in [const.OpType.INSTALL, const.OpType.REPLACE]:

            # 检查：除安装操作外，其他操作时内网IP是否存在
            if cloud_inner_ip not in inner_ip_info:
                error_host["msg"] = _("尚未被安装，无法执行 {op_type} 操作").format(
                    op_type=const.JOB_TYPE_DICT[data["op_type"] + "_" + data["node_type"]]
                )
                ip_filter_list.append(error_host)
                continue

            # 检查：除安装操作外，其他操作时检测Host ID是否正确
            if host["bk_host_id"] != inner_ip_info[cloud_inner_ip]["bk_host_id"]:
                error_host["msg"] = _("Host ID 不正确，无法执行 {op_type} 操作").format(
                    op_type=const.JOB_TYPE_DICT[data["op_type"] + "_" + data["node_type"]]
                )
                ip_filter_list.append(error_host)
                continue

            # 检查：除安装操作外，是否该Host正在执行任务
            if task_info.get(host["bk_host_id"], {}).get("status") in [
                "RUNNING",
                "PENDING",
            ]:
                error_host["msg"] = _("正在执行其他任务，无法执行新任务")
                error_host["exception"] = "is_running"
                error_host["job_id"] = task_info.get(host["bk_host_id"], {}).get("job_id")
                ip_filter_list.append(error_host)
                continue

            # 检查：节点类型是否与操作类型一致, 如本身为PROXY，重装却为AGENT
            # 此处不区分P-AGENT和AGENT
            if node_type not in inner_ip_info[cloud_inner_ip]["node_type"]:
                error_host["msg"] = _("节点类型不正确，该主机是 {host_node_type}, 而请求的操作类型是 {node_type}").format(
                    host_node_type=inner_ip_info[cloud_inner_ip]["node_type"], node_type=node_type
                )
                ip_filter_list.append(error_host)
                continue

        # 完全没问题，可进行下一步
        accept_list.append(dict(host))

    return ip_filter_list, accept_list, proxy_not_alive


def operate_validator(db_host_sql, user_biz: dict, username: str, task_info: dict, is_superuser: bool):
    """
    用于operate任务的校验
    :param db_host_sql: 用户操作主机的详细信息
    :param user_biz: 用户业务权限
    :param username: 用户名
    :param task_info: 任务信息
    :param is_superuser: 是否超管
    :return: 列表，ip被占用及其原因
    """

    # 可以进入下一步的Host ID
    permission_host_ids = []
    # 获得所有云区域ID
    bk_cloud_ids = [host["bk_cloud_id"] for host in db_host_sql]
    # 获得所有云区域信息
    cloud_info = CloudHandler().list_cloud_info(bk_cloud_ids)

    for host in db_host_sql:
        # 检查：是否有操作系统参数
        if not host.get("os_type") and host["node_type"] != const.NodeType.PROXY:
            raise NotExistsOs(_("主机(IP:{inner_ip}) 没有操作系统, 请【重装】并补全相关信息").format(inner_ip=host["inner_ip"]))

        # 是否有业务权限
        if not host["bk_biz_id"] in user_biz:
            raise BusinessNotPermissionError(_("您没有主机(IP:{inner_ip})的业务权限").format(inner_ip=host["inner_ip"]))

        # 云区域是否存在
        if not cloud_info.get(host["bk_cloud_id"]):
            raise CloudNotPermissionError(_("不允许操作【云区域不存在】的主机, 云区域id: {}").format(host["bk_cloud_id"]))

        if not settings.USE_IAM:
            # 是否有云区域权限
            if username not in cloud_info.get(host["bk_cloud_id"], {}).get("creator") and not is_superuser:
                raise CloudNotPermissionError(
                    _("您没有云区域 {bk_cloud_name} 的权限").format(
                        bk_cloud_name=cloud_info.get(host["bk_cloud_id"], {}).get("bk_cloud_name")
                    )
                )

        # 检查：是否该Host正在执行任务
        if task_info.get(host["bk_host_id"], {}).get("status") in [
            "RUNNING",
            "PENDING",
        ]:
            raise IpRunningJob(_("IP:{inner_ip} 正在执行其他任务，无法执行新任务").format(inner_ip=host["inner_ip"]))

        permission_host_ids.append(host["bk_host_id"])

    # 获得业务ID
    host_biz_scope = [host["bk_biz_id"] for host in db_host_sql]

    db_host_ids = [{"bk_host_id": host_id} for host_id in permission_host_ids]

    return db_host_ids, host_biz_scope
