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
import logging
import typing

from django.conf import settings
from django.db.models import QuerySet
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.core.ipchooser.constants import CommonEnum
from apps.core.ipchooser.handlers.host_handler import HostHandler
from apps.exceptions import ApiError, ValidationError
from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
from apps.node_man.periodic_tasks.sync_agent_status_task import (
    update_or_create_host_agent_status,
)
from apps.node_man.periodic_tasks.sync_proc_status_task import (
    update_or_create_proc_status,
)
from apps.utils import basic
from env.constants import GseVersion

from .tools import GrayTools

logger = logging.getLogger("app")


class GrayHandler:
    @classmethod
    def get_cloud_host_query_params(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]) -> typing.List[int]:
        """
        根据用户输入信息获取需要查询的主机ID列表
        """
        bk_host_ids: typing.List[int] = []

        # 没有带查询条件的，直接返回空列表
        if not validated_data.get("cloud_ips"):
            return bk_host_ids

        cloud_inner_ip_set: typing.Set[str] = set()
        cloud_inner_ipv6_set: typing.Set[str] = set()

        for cloud_ip in validated_data["cloud_ips"]:
            if not len(cloud_ip.split(":", 1)) == 2:
                raise ValidationError(
                    _("cloud_ip [{cloud_ip}] 格式输入有误, 请修改后重试 示例: 0:127.0.0.1".format(cloud_ip=cloud_ip))
                )

            cloud_id_str, inner_ip = cloud_ip.split(":", 1)
            if basic.is_v6(inner_ip):
                cloud_inner_ipv6_set.add(f"{cloud_id_str}{CommonEnum.SEP.value}{basic.exploded_ip(inner_ip)}")
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

        return {int(v1_ap_id): int(v2_ap_id) for v1_ap_id, v2_ap_id in gray_ap_map.items()}

    @classmethod
    def update_host_ap_by_host_ids(
        cls,
        host_ids: typing.Union[typing.List[int], typing.Set[int]],
        bk_biz_ids: typing.Union[typing.List[int], typing.Set[int]],
        is_biz_gray: bool,
        rollback: bool = False,
    ):

        gray_ap_map: typing.Dict[int, int] = cls.get_gray_ap_map()

        # 更新主机ap id
        for v1_ap_id, v2_ap_id in gray_ap_map.items():
            if rollback:
                # 如果是回滚将v1,v2 id进行对调
                v1_ap_id, v2_ap_id = v2_ap_id, v1_ap_id

            query_params: typing.Dict = {"bk_biz_id__in": bk_biz_ids, "ap_id": v1_ap_id}

            # 非业务整体灰度时，需要添加主机范围限制
            if not is_biz_gray:
                # 增加云区域主机查询参数
                query_params.update(bk_host_id__in=host_ids)

            logger.info(f"[update_host_ap_by_host_ids][rollback={rollback}] {v1_ap_id} to {v2_ap_id}")
            node_man_models.Host.objects.filter(**query_params).update(ap_id=v2_ap_id, updated_at=timezone.now())

            # 构造反向条件，异步更新 Agent / 插件状态
            query_params["ap_id"] = v2_ap_id
            host_queryset: QuerySet = node_man_models.Host.objects.filter(**query_params)

            if settings.BK_BACKEND_CONFIG:
                # 处在后台时，异步执行状态同步任务
                update_or_create_host_agent_status.delay(
                    task_id=f"update_host_ap_by_host_ids[rollback={rollback}]", host_queryset=host_queryset
                )
                update_or_create_proc_status.delay(task_id="update_host_ap_by_host_ids", host_queryset=host_queryset)
                logger.info(
                    f"[update_host_ap_by_host_ids][rollback={rollback}] "
                    f"Start to sync Agent & Plugin status asynchronously"
                )
            else:
                host_count: int = host_queryset.count()
                if host_count < node_man_constants.QUERY_AGENT_STATUS_HOST_LENS:
                    # 在 SaaS 端进行操作时，小批量主机的情况下优先同步 Agent 状态（耗时短）
                    logger.info(
                        f"[update_host_ap_by_host_ids][rollback={rollback}][saas] "
                        f"Start to sync Agent status, count -> {host_count}"
                    )
                    update_or_create_host_agent_status(
                        task_id=f"update_host_ap_by_host_ids[rollback={rollback}][saas]", host_queryset=host_queryset
                    )
                    logger.info(f"[update_host_ap_by_host_ids][rollback={rollback}][saas] Sync Agent status finished")
                else:
                    logger.info(
                        f"[update_host_ap_by_host_ids][rollback={rollback}][saas] "
                        f"Skip to sync agent status, count -> {host_count}"
                    )

    @classmethod
    def update_host_ap(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]], is_biz_gray: bool, rollback: bool = False
    ):

        clouds_ip_host_ids: typing.List[int] = cls.get_cloud_host_query_params(validated_data)

        cls.update_host_ap_by_host_ids(clouds_ip_host_ids, validated_data["bk_biz_ids"], is_biz_gray, rollback)

    @classmethod
    def update_gray_scope_list(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        # 使用最新的灰度列表进行更新，不走缓存
        gray_scope_list: typing.List[int] = GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False)
        if rollback:
            # 将业务从灰度列表中去除
            gray_scope_list: typing.List[int] = list(set(gray_scope_list) - set(validated_data["bk_biz_ids"]))
            logger.info(f"[update_gray_scope_list][rollback={rollback}] {set(validated_data['bk_biz_ids'])}")
        else:
            # 记录灰度业务
            gray_scope_list.extend(validated_data["bk_biz_ids"])
            logger.info(
                f"[update_gray_scope_list][rollback={rollback}] bk_biz_ids -> {set(validated_data['bk_biz_ids'])}"
            )

        node_man_models.GlobalSettings.update_config(
            node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, gray_scope_list
        )
        logger.info(f"[update_gray_scope_list][rollback={rollback}] commit to db")

        # 触发一次缓存主动更新
        GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False)
        logger.info("[update_gray_scope_list][rollback={rollback}] flush cache")

    @classmethod
    def update_cloud_ap_id(cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False):
        gray_ap_map: typing.Dict[int, int] = cls.get_gray_ap_map()
        gray_scope_list: typing.List[int] = GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False)

        clouds = (
            node_man_models.Host.objects.filter(bk_biz_id__in=validated_data["bk_biz_ids"])
            .values("bk_cloud_id")
            .distinct()
            .order_by("bk_cloud_id")
        )

        ap_id_obj_map: typing.Dict[int, node_man_models.AccessPoint] = node_man_models.AccessPoint.ap_id_obj_map()

        for cloud in clouds:
            cloud_obj: typing.Optional[node_man_models.Cloud] = node_man_models.Cloud.objects.filter(
                bk_cloud_id=cloud["bk_cloud_id"]
            ).first()

            # 跳过云区域不存在的情况
            if not cloud_obj:
                continue

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
                        # 当云区域覆盖的业务（cloud_bk_biz_ids）完全包含于灰度业务集（gray_scope_list）时，需要操作回滚
                        if not set(cloud_bk_biz_ids) - set(gray_scope_list):
                            cloud_obj.ap_id = v1_ap_id
                            cloud_obj.save()
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V1.value and rollback:
                # 回滚情况且云区域接入点版本为V1不需处理
                continue
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V2.value:
                # 非rollback且云区域接入点版本为V2不需处理
                continue
            else:
                # 当云区域覆盖的业务（cloud_bk_biz_ids）完全包含于灰度业务集（gray_scope_list）时，需要操作灰度
                if not set(cloud_bk_biz_ids) - set(gray_scope_list):
                    try:
                        cloud_obj.ap_id = gray_ap_map[cloud_obj.ap_id]
                        cloud_obj.save()
                    except KeyError:
                        raise ApiError(
                            _("缺少云区域 -> {bk_cloud_name} ID -> {bk_cloud_id}, 接入点版本的映射关系，请联系管理员").format(
                                bk_cloud_name=cloud_obj.bk_cloud_name, bk_cloud_id=cloud_obj.bk_cloud_id
                            )
                        )

    @classmethod
    @atomic
    def build(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):

        # 不传 cloud_ips 表示按业务灰度
        is_biz_gray: bool = "cloud_ips" not in validated_data

        if is_biz_gray:
            # 更新灰度业务范围
            cls.update_gray_scope_list(validated_data)

            # 更新云区域接点
            cls.update_cloud_ap_id(validated_data)

        # 更新主机ap
        cls.update_host_ap(validated_data, is_biz_gray)

    @classmethod
    @atomic
    def rollback(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):

        # 不传 cloud_ips 表示按业务灰度
        is_biz_gray: bool = "cloud_ips" not in validated_data

        if is_biz_gray:
            # 需要先回滚云区域，确保业务移除灰度列表前能正常判定云区域所属关系
            # 更新云区域接入点
            cls.update_cloud_ap_id(validated_data, rollback=True)

            # 更新灰度业务范围
            cls.update_gray_scope_list(validated_data, rollback=True)

        # 更新主机ap
        cls.update_host_ap(validated_data, is_biz_gray, rollback=True)
