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

from apps.core.concurrent.cache import FuncCacheDecorator
from apps.exceptions import ApiError
from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
from apps.utils.redis import DynamicContainer, RedisDict
from env.constants import GseVersion


class GrayTools:
    @classmethod
    @FuncCacheDecorator(cache_time=20 * node_man_constants.TimeUnit.SECOND)
    def get_or_create_gse2_gray_scope_list(cls) -> typing.List[int]:
        """
        获取 GSE2.0 灰度列表
        :return:
        """
        gray_scope_list_or_none: typing.Optional[typing.List[int]] = node_man_models.GlobalSettings.get_config(
            node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, default=None
        )
        if gray_scope_list_or_none is not None:
            return gray_scope_list_or_none

        node_man_models.GlobalSettings.set_config(node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, [])
        return []

    def __init__(self):
        self.gse2_gray_scope_set: typing.Set[int] = set(self.get_or_create_gse2_gray_scope_list(get_cache=True))
        self.ap_id_obj_map: typing.Dict[int, node_man_models.AccessPoint] = node_man_models.AccessPoint.ap_id_obj_map()

    def is_gse2_gray(self, bk_biz_id: typing.Any) -> bool:
        """
        指定业务是否属于 GSE2.0 灰度
        :param bk_biz_id: 业务 ID
        :return:
        """
        return bk_biz_id in self.gse2_gray_scope_set

    def get_host_ap_gse_version(self, bk_biz_id: typing.Any, ap_id: int, is_install_other_agent: bool = False) -> str:
        """
        :return 返回当前主机应使用的 GSE VERSION
        """
        if is_install_other_agent:
            # 注入AP ID 优先使用注入AP 的GSE 版本
            gse_version: str = self.ap_id_obj_map[ap_id].gse_version
        elif self.is_gse2_gray(bk_biz_id):
            # 业务整体处于 2.0 灰度
            gse_version: str = GseVersion.V2.value
        elif ap_id == node_man_constants.DEFAULT_AP_ID:
            # 业务不处于整体灰度中，并且关联默认接入点，视为灰度范围之外
            gse_version: str = GseVersion.V1.value
        else:
            # 具有明确的接入点
            gse_version: str = self.ap_id_obj_map[ap_id].gse_version
        return gse_version

    def inject_meta_to_instances(
        self, instances: typing.Dict[str, typing.Dict[str, typing.Union[typing.Dict, typing.Any]]], data_backend: str
    ):
        """
        在 instances 中注入 Meta 信息
        :param instances:
        :return:
        """
        injected_instances: typing.Union[RedisDict, dict] = DynamicContainer(data_backend=data_backend).container
        bk_host_ids: typing.Set[int] = {
            instance_info["host"]["bk_host_id"]
            for instance_info in instances.values()
            if instance_info["host"].get("bk_host_id")
        }
        host_infos: typing.List[typing.Dict[str, typing.Any]] = node_man_models.Host.objects.filter(
            bk_host_id__in=bk_host_ids
        ).values("bk_host_id", "ap_id")
        host_id__ap_id_map: typing.Dict[int, typing.Optional[int]] = {}
        job_task_policy: typing.Dict[str, typing.List[int]] = node_man_models.GlobalSettings.get_config(
            key=node_man_models.GlobalSettings.KeyEnum.JOB_TASK_POLICY.value, default={}
        )
        biz_ids_list: typing.List[int] = job_task_policy.get(node_man_constants.BkJobScopeType.BIZ.value, [])

        for host_info in host_infos:
            host_id__ap_id_map[host_info["bk_host_id"]] = host_info["ap_id"]

        for instance_id, instance_info in instances.items():
            host_info = instance_info["host"]
            # 优先取 host_info 中的 ap_id，用于 Agent 操作场景下确定 ap
            ap_id: typing.Optional[int] = host_info.get("ap_id") or host_id__ap_id_map.get(host_info.get("bk_host_id"))
            meta: typing.Dict[str, typing.Any] = {}
            if host_info.get("is_need_inject_ap_id"):
                # 双如果为安装额外Agent 将ap_id 注入 meta
                meta["AP_ID"] = ap_id
            bk_biz_id = host_info.get("bk_biz_id")
            if bk_biz_id in biz_ids_list:
                meta["SCOPE_ID"] = bk_biz_id
                meta["SCOPE_TYPE"] = node_man_constants.BkJobScopeType.BIZ.value
            gse_version: str = self.get_host_ap_gse_version(
                bk_biz_id=bk_biz_id,
                ap_id=ap_id,
                is_install_other_agent=host_info.get("is_need_inject_ap_id"),
            )
            meta["GSE_VERSION"] = gse_version
            instance_info["meta"] = meta

            injected_instances[instance_id] = instance_info

        return injected_instances

    @classmethod
    def get_gray_ap_map(cls) -> typing.Dict[int, int]:
        # 获取GSE2.0灰度 接入点映射关系
        gray_ap_map: typing.Dict[int, int] = node_man_models.GlobalSettings.get_config(
            key=node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value,
            default={},
        )

        if not gray_ap_map:
            raise ApiError(_("请联系管理员配置GSE1.0-2.0接入点映射"))

        return {int(v1_ap_id): int(v2_ap_id) for v1_ap_id, v2_ap_id in gray_ap_map.items()}
