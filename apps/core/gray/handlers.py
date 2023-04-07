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

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

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
    def get_query_host_params(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]) -> Q:
        """
        根据用户输入信息生成主机查询参数
        """
        if validated_data.get("bk_biz_ids"):
            # 全业务进入灰度
            query_params = Q(bk_biz_id__in=validated_data["bk_biz_ids"])
        elif validated_data.get("cloud_ips"):
            # 用户输入主机忽略业务参数
            cloud_hosts__map: typing.Dict[int, typing.Dict[str, typing.List[str]]] = defaultdict(dict)

            for cloud_ip in validated_data["cloud_ips"]:
                if not len(cloud_ip.split(":")) == 2:
                    raise ValidationError(_("cloud_ip {} 格式输入有误, 请修改后重试 示例: 0:127.0.0.1"))
                bk_cloud_id = int(cloud_ip.split(":")[0])
                inner_ip = cloud_ip.split(":")[1]
                if basic.is_v6(inner_ip):
                    cloud_hosts__map[bk_cloud_id].setdefault("inner_ipv6", []).append(basic.exploded_ip(inner_ip))
                else:
                    cloud_hosts__map[bk_cloud_id].setdefault("inner_ip", []).append(inner_ip)

            # 组装参数
            query_params = Q()
            query_params.connector = "OR"
            for cloud_id, hosts in cloud_hosts__map.items():
                cloud_query_params = Q()
                cloud_query_params.connector = "AND"

                ip_type_query_params = Q()
                ip_type_query_params.connector = "OR"

                for ip_type, inner_ip_list in hosts.items():
                    ip_type_query_params.children.append((f"{ip_type}__in", inner_ip_list))

                cloud_query_params.children.append(("bk_cloud_id", cloud_id))
                cloud_query_params.children.append(ip_type_query_params)

                query_params.children.append(cloud_query_params)
        else:
            # 业务列表或者主机列表必须传其中之一
            raise ValidationError(_("业务列表或者主机列表必选其一"))

        return query_params

    @classmethod
    def update_host_ap(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        query_host_params: Q = cls.get_query_host_params(validated_data)

        # 获取GSE2.0灰度 接入点映射关系
        gray_ap_map: typing.Dict[int, int] = node_man_models.GlobalSettings.get_config(
            key=node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value,
            default={},
        )

        if not gray_ap_map:
            raise ApiError(_("请联系管理员配置GSE1.0-2.0接入点映射"))

        # 更新主机ap id
        for v1_ap_id, v2_ap_id in gray_ap_map.items():
            if rollback:
                # 如果是回滚将v1,v2 id进行对调
                v1_ap_id, v2_ap_id = v2_ap_id, v1_ap_id
            node_man_models.Host.objects.filter(query_host_params, ap_id=int(v1_ap_id)).update(ap_id=int(v2_ap_id))

    @classmethod
    def update_gray_scope_list(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        # 记录灰度业务
        if validated_data.get("bk_biz_ids", []):
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
    def build(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):
        # 更新主机ap
        cls.update_host_ap(validated_data)

        # 更新灰度业务范围
        cls.update_gray_scope_list(validated_data)

    @classmethod
    def rollback(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):
        # 更新主机ap
        cls.update_host_ap(validated_data, rollback=True)

        # 更新灰度业务范围
        cls.update_gray_scope_list(validated_data, rollback=True)
