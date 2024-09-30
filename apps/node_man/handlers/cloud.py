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
from django.conf import settings
from django.db.models.aggregates import Count
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _

from apps.exceptions import ValidationError
from apps.node_man import constants as const
from apps.node_man.constants import DEFAULT_CLOUD, DEFAULT_CLOUD_NAME, IamActionType
from apps.node_man.exceptions import CloudNotExistError, CloudUpdateHostError
from apps.node_man.handlers.cmdb import CmdbHandler
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.models import (
    AccessPoint,
    Cloud,
    GlobalSettings,
    Host,
    IdentityData,
    ProcessStatus,
)
from apps.utils import APIModel
from apps.utils.local import get_request_username


class CloudHandler(APIModel):
    """
    管控区域API处理器
    """

    def retrieve(self, bk_cloud_id: int):
        """
        查询管控区域详情
        :param bk_cloud_id: 管控区域id
        """
        cloud = Cloud.objects.filter(pk=bk_cloud_id).first()
        if cloud is None:
            raise CloudNotExistError(_("不存在ID为: {bk_cloud_id} 的「管控区域」").format(bk_cloud_id=bk_cloud_id))

        # 获得接入点名称
        ap_name = dict(AccessPoint.objects.values_list("id", "name"))
        ap_name[-1] = _("自动选择接入点")

        # 获得isp信息
        isps = GlobalSettings().fetch_isp()
        isp_name = isps.get(cloud.isp, {}).get("isp_name", cloud.isp)
        isp_icon = isps.get(cloud.isp, {}).get("isp_icon", "")
        ap_name = ap_name.get(cloud.ap_id)
        return {
            "bk_cloud_id": cloud.bk_cloud_id,
            "bk_cloud_name": cloud.bk_cloud_name,
            "isp": cloud.isp,
            "ap_id": cloud.ap_id,
            "isp_name": isp_name,
            "isp_icon": isp_icon,
            "ap_name": ap_name,
        }

    def list(self, params):
        """
        查询管控区域列表
        :param params: 参数
        :return: 管控区域列表
        """

        # 管控区域查看、编辑、删除、创建权限
        if settings.USE_IAM:
            clouds = list(Cloud.objects.values("bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "is_visible"))
            perms = IamHandler().fetch_policy(
                get_request_username(),
                [
                    IamActionType.cloud_view,
                    IamActionType.cloud_edit,
                    IamActionType.cloud_delete,
                    IamActionType.cloud_create,
                ],
            )
        else:
            if IamHandler.is_superuser(get_request_username()):
                clouds = list(Cloud.objects.values("bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "is_visible"))
            else:
                clouds = list(
                    Cloud.objects.filter(creator__contains=get_request_username()).values(
                        "bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "is_visible"
                    )
                )
            cloud_ids = [cloud["bk_cloud_id"] for cloud in clouds]
            perms = {
                IamActionType.cloud_view: cloud_ids,
                IamActionType.cloud_edit: cloud_ids,
                IamActionType.cloud_delete: cloud_ids,
            }

        view_perm = perms[IamActionType.cloud_view]
        edit_perm = perms[IamActionType.cloud_edit]
        delete_perm = perms[IamActionType.cloud_delete]

        # 是否返回直连区域
        if params["with_default_area"]:
            clouds.insert(0, {"bk_cloud_id": const.DEFAULT_CLOUD, "bk_cloud_name": _("直连区域")})

        # 用户默认拥有直连区域使用权限
        view_perm.insert(0, 0)

        # 获得相同bk_cloud_id的Host个数
        hosts_count = dict(
            Host.objects.filter(node_type=const.NodeType.PAGENT)
            .values_list("bk_cloud_id")
            .annotate(node_count=Count("bk_cloud_id"))
            .order_by()
        )

        # 获得同一管控区域下的Proxy内网IP
        cloud_proxies = {}
        proxies_cloud_ip = Host.objects.filter(node_type=const.NodeType.PROXY).values(
            "bk_cloud_id", "inner_ip", "inner_ipv6", "outer_ip", "outer_ipv6", "bk_host_id", "bk_agent_id"
        )
        for proxy in proxies_cloud_ip:
            if proxy["bk_cloud_id"] not in cloud_proxies:
                cloud_proxies[proxy["bk_cloud_id"]] = [proxy]
            else:
                cloud_proxies[proxy["bk_cloud_id"]].append(proxy)

        # 获得接入点名称
        ap_name = dict(AccessPoint.objects.values_list("id", "name"))
        # 配置自动选择接入点
        ap_name[-1] = _("自动选择接入点")
        # 获得isp信息
        isps = GlobalSettings().fetch_isp()

        # 获得管控区域内异常的Proxy
        cloud_exception = {}
        proxies = dict(
            Host.objects.filter(
                bk_cloud_id__in=[cloud["bk_cloud_id"] for cloud in clouds], node_type=const.NodeType.PROXY
            ).values_list("bk_host_id", "bk_cloud_id")
        )
        identities = {
            identity["bk_host_id"]: {"password": identity["password"], "key": identity["key"]}
            for identity in IdentityData.objects.filter(bk_host_id__in=list(proxies.keys())).values(
                "bk_host_id", "password", "key"
            )
        }
        process_status = dict(
            ProcessStatus.objects.filter(
                bk_host_id__in=list(proxies.keys()), proc_type=const.ProcType.AGENT
            ).values_list("bk_host_id", "status")
        )
        for proxy in proxies:
            # exception为status则说明有状态异常代理，为overdue则说明有过期代理，为空时说明正常
            # 两者同时出现时，以状态异常为优先
            if process_status.get(proxy, const.ProcStateType.UNKNOWN) != const.ProcStateType.RUNNING:
                cloud_exception[proxies[proxy]] = "abnormal"
            elif (
                not identities.get(proxy, {}).get("password")
                and not identities.get(proxy, {}).get("key")
                and cloud_exception.get(proxies[proxy]) != "abnormal"
            ):
                cloud_exception[proxies[proxy]] = "overdue"

        for cloud in clouds:
            cloud["node_count"] = hosts_count.get(cloud["bk_cloud_id"], 0)
            cloud["proxy_count"] = len(cloud_proxies.get(cloud["bk_cloud_id"], []))
            cloud["ap_name"] = ap_name.get(cloud.get("ap_id"))
            cloud["isp_name"] = isps.get(cloud.get("isp"), {}).get("isp_name", cloud.get("isp"))
            cloud["isp_icon"] = isps.get(cloud.get("isp"), {}).get("isp_icon", "")
            cloud["exception"] = cloud_exception.get(cloud["bk_cloud_id"], "")
            cloud["proxies"] = cloud_proxies.get(cloud["bk_cloud_id"])
            cloud["permissions"] = {
                "view": cloud["bk_cloud_id"] in view_perm,
                "edit": cloud["bk_cloud_id"] in edit_perm,
                "delete": cloud["bk_cloud_id"] in delete_perm,
            }
            # 统计存活的 Proxy 数量
            alive_proxies = []
            for proxy_info in cloud_proxies.get(cloud["bk_cloud_id"]) or []:
                if (
                    process_status.get(proxy_info["bk_host_id"], const.ProcStateType.UNKNOWN)
                    == const.ProcStateType.RUNNING
                ):
                    alive_proxies.append(proxy_info)
            cloud["alive_proxy_count"] = len(alive_proxies)

        return clouds

    def create(self, params: dict, username: str):
        """
        创建管控区域
        :param params: 存有各个参数的值
        :param username: 用户名
        """

        bk_cloud_name = params["bk_cloud_name"]
        bk_cloud_vendor = const.CMDB_CLOUD_VENDOR_MAP.get(params["isp"])
        bk_cloud_id = CmdbHandler.get_or_create_cloud(bk_cloud_name, bk_cloud_vendor=bk_cloud_vendor)

        if bk_cloud_name == str(DEFAULT_CLOUD_NAME):
            raise ValidationError(_("管控区域不可名为「直连区域」"))

        created = Cloud.objects.filter(bk_cloud_name=params["bk_cloud_name"]).exists()
        if created:
            raise ValidationError(_("管控区域名称不可重复"))

        with atomic():
            cloud = Cloud.objects.create(
                bk_cloud_id=bk_cloud_id,
                isp=params["isp"],
                ap_id=params["ap_id"],
                bk_cloud_name=params["bk_cloud_name"],
                creator=[username],
            )

            if settings.USE_IAM:
                # 将创建者返回权限中心
                ok, message = IamHandler.return_resource_instance_creator(
                    "cloud", bk_cloud_id, params["bk_cloud_name"], username
                )
                if not ok:
                    raise PermissionError(_("权限中心创建关联权限失败: {}".format(message)))

            return {"bk_cloud_id": cloud.bk_cloud_id}

    @staticmethod
    def update(bk_cloud_id: int, bk_cloud_name: str, isp: str, ap_id: int):
        """
        编辑管控区域
        """
        cloud = Cloud.objects.get(pk=bk_cloud_id)
        if Cloud.objects.filter(bk_cloud_name=bk_cloud_name).exclude(bk_cloud_id=bk_cloud_id).exists():
            raise ValidationError(_("管控区域名称不可重复"))

        # 向CMDB修改管控区域名称以及云服务商
        bk_cloud_vendor: str = const.CMDB_CLOUD_VENDOR_MAP.get(isp)
        CmdbHandler.rename_cloud(bk_cloud_id, bk_cloud_name, bk_cloud_vendor=bk_cloud_vendor)

        cloud.bk_cloud_name = bk_cloud_name
        cloud.isp = isp
        cloud.ap_id = ap_id
        cloud.save()

    def destroy(self, bk_cloud_id: int):
        """
        删除管控区域
        :param bk_cloud_id: 管控区域ID
        """

        hosted = Host.objects.filter(bk_cloud_id=bk_cloud_id).exists()
        if hosted:
            raise CloudUpdateHostError(_("该区域已存在主机"))

        # 向云端删除管控区域
        CmdbHandler.delete_cloud(bk_cloud_id)
        Cloud.objects.filter(bk_cloud_id=bk_cloud_id).delete()

    def list_cloud_info(self, bk_cloud_ids):
        """
        获得相应管控区域 id, name, ap_id
        :param bk_cloud_ids: 管控区域ID列表集合
        :return
        {
            cloud_id: {
                'bk_cloud_name': name,
                'ap_id': id,
                'creator': username
            }
        }
        """
        clouds = list(
            Cloud.objects.filter(bk_cloud_id__in=bk_cloud_ids).values(
                "bk_cloud_id", "bk_cloud_name", "ap_id", "creator"
            )
        )
        cloud_info = {
            cloud["bk_cloud_id"]: {
                "ap_id": cloud["ap_id"],
                "creator": cloud["creator"],
                "bk_cloud_id": cloud["bk_cloud_id"],
                "bk_cloud_name": cloud["bk_cloud_name"],
            }
            for cloud in clouds
        }
        cloud_info[0] = {
            "bk_cloud_id": DEFAULT_CLOUD,
            "bk_cloud_name": str(DEFAULT_CLOUD_NAME),
            "ap_id": const.DEFAULT_AP_ID,
            "creator": [get_request_username()],
        }
        return cloud_info

    def list_cloud_name(self):
        """
        返回用户有权限的管控区域ID及对应名称
        :return: 管控区域ID及对应名称
        """

        return dict(
            Cloud.objects.filter(
                creator__contains=get_request_username(),
                bk_cloud_id__in=IamHandler().fetch_policy(get_request_username(), [IamActionType.cloud_view])[
                    IamActionType.cloud_view
                ],
            ).values_list("bk_cloud_id", "bk_cloud_name")
        )

    def list_cloud_biz(self, bk_cloud_id):
        """
        查询管控区域下的业务ID
        :param bk_cloud_id: 管控区域ID
        """
        # 查询管控区域下的主机的全部业务
        return list(
            Host.objects.filter(bk_cloud_id=bk_cloud_id)
            .values_list("bk_biz_id", flat=True)
            .order_by("bk_biz_id")
            .distinct()
        )
