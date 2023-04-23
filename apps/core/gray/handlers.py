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

from django.utils.translation import ugettext_lazy as _

from apps.core.ipchooser.constants import CommonEnum
from apps.core.ipchooser.handlers.host_handler import HostHandler
from apps.exceptions import ApiError, ValidationError
from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
from apps.utils import basic
from env.constants import GseVersion

from ...utils.cache import func_cache_decorator


class GrayTools:
    @classmethod
    @func_cache_decorator(cache_time=10 * node_man_constants.TimeUnit.SECOND)
    def get_gse2_gray_scope_list(cls) -> typing.List[int]:
        """
        获取 GSE2.0 灰度列表
        :return:
        """
        return node_man_models.GlobalSettings.get_config(
            node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, default=[]
        )

    @classmethod
    def is_gse2_gray(cls, bk_biz_id: typing.Any) -> bool:
        """
        指定业务是否属于 GSE2.0 灰度
        :param bk_biz_id: 业务 ID
        :return:
        """
        return bk_biz_id in set(cls.get_gse2_gray_scope_list(get_cache=True))

    @classmethod
    def get_host_ap_gse_version(
        cls, bk_biz_id: int, ap_id: int, ap_id_obj_map: typing.Dict[int, node_man_models.AccessPoint]
    ) -> str:
        """
        :return 返回当前主机应使用的GSE VERSION
        """
        if GrayTools.is_gse2_gray(bk_biz_id):
            # 业务整体处于 2.0 灰度
            gse_version: str = GseVersion.V2.value
        elif ap_id == node_man_constants.DEFAULT_AP_ID:
            # 业务不处于整体灰度中，并且关联默认接入点，视为灰度范围之外
            gse_version: str = GseVersion.V1.value
        else:
            # 具有明确的接入点
            gse_version: str = ap_id_obj_map[ap_id].gse_version
        return gse_version

    @classmethod
    def inject_meta_to_instances(
        cls, instances: typing.Dict[str, typing.Dict[str, typing.Union[typing.Dict, typing.Any]]]
    ):
        """
        在 instances 中注入 Meta 信息
        :param instances:
        :return:
        """
        ap_id_obj_map: typing.Dict[
            typing.Optional[int], node_man_models.AccessPoint
        ] = node_man_models.AccessPoint.ap_id_obj_map()
        bk_host_ids: typing.Set[int] = {
            instance_info["host"]["bk_host_id"]
            for instance_info in instances.values()
            if instance_info["host"].get("bk_host_id")
        }
        host_infos: typing.List[typing.Dict[str, typing.Any]] = node_man_models.Host.objects.filter(
            bk_host_id__in=bk_host_ids
        ).values("bk_host_id", "ap_id")
        host_id__ap_id_map: typing.Dict[int, typing.Optional[int]] = {}

        for host_info in host_infos:
            host_id__ap_id_map[host_info["bk_host_id"]] = host_info["ap_id"]

        for instance_id, instance_info in instances.items():
            host_info = instance_info["host"]
            # 优先取 host_info 中的 ap_id，用于 Agent 操作场景下确定 ap
            ap_id: typing.Optional[int] = host_info.get("ap_id") or host_id__ap_id_map.get(host_info.get("bk_host_id"))

            gse_version: str = GrayTools.get_host_ap_gse_version(
                bk_biz_id=host_info.get("bk_biz_id"), ap_id=ap_id, ap_id_obj_map=ap_id_obj_map
            )

            instance_info["meta"] = {"GSE_VERSION": gse_version}

    @classmethod
    def inject_meta_to_hosts(cls, hosts: typing.Dict[str, typing.Any]):
        """
        在 hosts 中注入 Meta 信息，要求 host 信息中带接入点
        :param hosts:
        :return:
        """
        #


class GrayHandler:
    @classmethod
    def get_cloud_host_query_params(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]) -> typing.List[int]:
        """
        根据用户输入信息获取需要查询的主机ID列表
        """
        bk_host_ids: typing.List[int] = []

        if validated_data.get("cloud_ips"):
            cloud_inner_ip_set: typing.Set[str] = set()
            cloud_inner_ipv6_set: typing.Set[str] = set()

            for cloud_ip in validated_data["cloud_ips"]:
                if not len(cloud_ip.split(":")) == 2:
                    raise ValidationError(
                        _("cloud_ip [{cloud_ip}] 格式输入有误, 请修改后重试 示例: 0:127.0.0.1".format(cloud_ip=cloud_ip))
                    )

                inner_ip = cloud_ip.split(":")[1]
                if basic.is_v6(inner_ip):
                    cloud_inner_ipv6_set.add(
                        f"{cloud_ip.split(':')[0]}{CommonEnum.SEP.value}{basic.exploded_ip(inner_ip)}"
                    )
                else:
                    cloud_inner_ip_set.add(cloud_ip)

            or_conditions = [
                {"key": "cloud_inner_ip", "val": cloud_inner_ip_set},
                {"key": "cloud_inner_ipv6", "val": cloud_inner_ipv6_set},
            ]
            hosts = HostHandler.details_base(
                scope_list=[{"bk_biz_id": biz_id} for biz_id in validated_data["bk_biz_ids"]],
                or_conditions=or_conditions,
            )

            bk_host_ids = [host["host_id"] for host in hosts]

        return bk_host_ids

    @classmethod
    def get_gray_ap_map(cls) -> typing.Dict[int, int]:
        # 获取GSE2.0灰度 接入点映射关系
        gray_ap_map: typing.Dict[int, int] = node_man_models.GlobalSettings.get_config(
            key=node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value,
            default={},
        )

        if not gray_ap_map:
            raise ApiError(_("请联系管理员配置GSE1.0-2.0接入点映射"))

        return gray_ap_map

    @classmethod
    def update_host_ap(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        if "clouds_ip" in validated_data and not validated_data["clouds_ip"]:
            # 用户传入clouds_ip 但是为空列表，不作更新处理, 认为是灰度了0个IP
            return

        clouds_ip_host_ids: typing.List[int] = cls.get_cloud_host_query_params(validated_data)

        gray_ap_map: typing.Dict[str, int] = cls.get_gray_ap_map()

        # 更新主机ap id
        for v1_ap_id, v2_ap_id in gray_ap_map.items():
            if rollback:
                # 如果是回滚将v1,v2 id进行对调
                v1_ap_id, v2_ap_id = v2_ap_id, v1_ap_id

            query_params: typing.Dict = {
                "bk_biz_id__in": validated_data["bk_biz_ids"],
                "ap_id": int(v1_ap_id),
            }

            if clouds_ip_host_ids:
                # 增加云区域主机查询参数
                query_params.update(bk_host_id__in=clouds_ip_host_ids)

            node_man_models.Host.objects.filter(**query_params).update(ap_id=int(v2_ap_id))

    @classmethod
    def update_gray_scope_list(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        # 如果用户没有传cloud_ips参数更新灰度业务
        if "cloud_ips" not in validated_data:
            gray_scope_list: typing.List[int] = GrayTools.get_gse2_gray_scope_list(get_cache=True)
            if rollback:
                # 将业务从灰度列表中去除
                gray_scope_list: typing.List[int] = list(set(gray_scope_list) - set(validated_data["bk_biz_ids"]))
            else:
                # 记录灰度业务
                gray_scope_list.extend(validated_data["bk_biz_ids"])

            node_man_models.GlobalSettings.update_config(
                node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, gray_scope_list
            )

    @classmethod
    def update_cloud_ap_id(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        gray_scope_list: typing.List[int] = node_man_models.GlobalSettings.get_config(
            key=node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value,
            default=[],
        )
        gray_ap_map: typing.Dict[str, int] = cls.get_gray_ap_map()

        clouds = (
            node_man_models.Host.objects.filter(bk_biz_id__in=validated_data["bk_biz_ids"])
            .values("bk_cloud_id")
            .distinct()
            .order_by("bk_cloud_id")
        )

        ap_id_obj_map: typing.Dict[int, node_man_models.AccessPoint] = node_man_models.AccessPoint.ap_id_obj_map()

        for cloud in clouds:
            cloud_obj = node_man_models.Cloud.objects.filter(bk_cloud_id=cloud["bk_cloud_id"]).first()

            cloud_bizs = (
                node_man_models.Host.objects.filter(bk_cloud_id=cloud["bk_cloud_id"])
                .values("bk_biz_id")
                .distinct()
                .order_by("bk_biz_id")
            )
            cloud_bk_biz_ids: typing.List[int] = [cloud_biz["bk_biz_id"] for cloud_biz in cloud_bizs]

            if ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V2.value and rollback:
                # 回滚V2到V1
                for v1_ap_id, v2_ap_id in gray_ap_map.items():
                    if cloud_obj.ap_id == v2_ap_id:
                        if set(cloud_bk_biz_ids) - set(gray_scope_list):
                            # 灰度范围已包含当前云区不包含当前云区域下的所有业务
                            cloud_obj.ap_id = v1_ap_id
                            cloud_obj.save()
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V1.value and rollback:
                # 回滚情况且云区域接入点版本为V1不需处理
                continue
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V2.value:
                # 非rollback且云区域接入点版本为V2不需处理
                continue
            else:
                # 常规灰度
                if not set(cloud_bk_biz_ids) - set(gray_scope_list):
                    # 灰度范围已包含当前云区域所有业务，云区域进入灰度
                    try:
                        cloud_obj.ap_id = gray_ap_map[str(cloud_obj.ap_id)]
                        cloud_obj.save()
                    except KeyError:
                        raise ApiError(
                            _("缺少云区域 -> {bk_cloud_name} ID -> {bk_cloud_id}, 接入点版本的映射关系，请联系管理员").format(
                                bk_cloud_name=cloud_obj.bk_cloud_name, bk_cloud_id=cloud_obj.bk_cloud_id
                            )
                        )

    @classmethod
    def build(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):
        # 更新主机ap
        cls.update_host_ap(validated_data)

        # 更新灰度业务范围
        cls.update_gray_scope_list(validated_data)

        # 更新云区域接点
        cls.update_cloud_ap_id(validated_data)

    @classmethod
    def rollback(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):
        # 更新主机ap
        cls.update_host_ap(validated_data, rollback=True)

        # 更新灰度业务范围
        cls.update_gray_scope_list(validated_data, rollback=True)

        # 更新云区域接点
        cls.update_cloud_ap_id(validated_data, rollback=True)
