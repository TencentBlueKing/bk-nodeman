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

from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
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
        ).values_list("bk_host_id", "ap_id")
        host_id__ap_id_map: typing.Dict[int, typing.Optional[int]] = {}

        for host_info in host_infos:
            host_id__ap_id_map[host_info["bk_host_id"]] = host_info["ap_id"]

        for instance_id, instance_info in instances.items():
            host_info = instance_info["host"]
            # 优先取 host_info 中的 ap_id，用于 Agent 操作场景下确定 ap
            ap_id: typing.Optional[int] = host_info.get("ap_id") or host_id__ap_id_map.get(host_info.get("bk_host_id"))

            if GrayTools.is_gse2_gray(host_info.get("bk_biz_id")):
                # 业务整体处于 2.0 灰度，设置灰度 Meta
                instance_info["meta"] = {"GSE_VERSION": GseVersion.V2.value}
            elif ap_id == node_man_constants.DEFAULT_AP_ID:
                # 业务不处于整体灰度中，并且关联默认接入点，视为灰度范围之外
                instance_info["meta"] = {"GSE_VERSION": GseVersion.V1.value}
            else:
                # 具有明确的接入点，根据接入点设置 Meta
                instance_info["meta"] = {"GSE_VERSION": ap_id_obj_map[ap_id].gse_version}

    @classmethod
    def inject_meta_to_hosts(cls, hosts: typing.Dict[str, typing.Any]):
        """
        在 hosts 中注入 Meta 信息，要求 host 信息中带接入点
        :param hosts:
        :return:
        """
        #


class GrayHandler:
    pass
