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
from django.db.models import F, QuerySet
from django.db.transaction import atomic
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.adapters.api.gse import get_gse_api_helper
from apps.core.ipchooser.constants import CommonEnum
from apps.core.ipchooser.handlers.host_handler import HostHandler
from apps.exceptions import ApiError, ValidationError
from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
from apps.node_man.handlers.job import JobHandler
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
        return GrayTools.get_gray_ap_map()

    @classmethod
    def activate(
        cls, host_nodes: typing.List[typing.Dict[str, int]], rollback: bool, only_status: bool = True
    ) -> typing.Dict[str, typing.Any]:

        if not host_nodes:
            logger.info(f"[activate][rollback={rollback}] Empty host nodes")
            return {}

        bk_biz_ids: typing.Set[int] = set()
        bk_host_ids: typing.Set[int] = set()

        for host_node in host_nodes:
            bk_biz_ids.add(host_node["bk_biz_id"])
            bk_host_ids.add(host_node["bk_host_id"])

        host_queryset: QuerySet = node_man_models.Host.objects.filter(
            bk_biz_id__in=bk_biz_ids, bk_host_id__in=bk_host_ids
        )

        if settings.BK_BACKEND_CONFIG:
            # 处在后台时，异步执行状态同步任务
            update_or_create_host_agent_status.delay(
                task_id=f"activate[rollback={rollback}]", host_queryset=host_queryset
            )
            update_or_create_proc_status.delay(task_id="update_host_ap_by_host_ids", host_queryset=host_queryset)
            logger.info(f"[activate][rollback={rollback}] Start to sync Agent & Plugin status asynchronously")
        else:
            host_count: int = host_queryset.count()
            if host_count < node_man_constants.QUERY_AGENT_STATUS_HOST_LENS:
                # 在 SaaS 端进行操作时，小批量主机的情况下优先同步 Agent 状态（耗时短）
                logger.info(f"[activate][rollback={rollback}][saas] Start to sync Agent status, count -> {host_count}")
                update_or_create_host_agent_status(
                    task_id=f"[activate][rollback={rollback}][saas]", host_queryset=host_queryset
                )
                logger.info(f"[activate][rollback={rollback}][saas] Sync Agent status finished")
            else:
                logger.info(f"[activate][rollback={rollback}][saas] Skip to sync agent status, count -> {host_count}")

        if only_status:
            logger.info(f"[activate][rollback={rollback}] Skip to create active job")
            return {}

        operate_result: typing.Dict[str, typing.Any] = JobHandler().operate(
            node_man_constants.JobType.ACTIVATE_AGENT, host_nodes, bk_biz_ids, {}, {}
        )
        logger.info(f"[activate][rollback={rollback}] Start to activate -> {operate_result}")

        return operate_result

    @classmethod
    def update_host_ap_by_host_ids(
        cls,
        host_ids: typing.Union[typing.List[int], typing.Set[int]],
        bk_biz_ids: typing.Union[typing.List[int], typing.Set[int]],
        is_biz_gray: bool,
        rollback: bool = False,
    ) -> typing.Dict[str, typing.Any]:

        host_nodes: typing.List[typing.Dict[str, int]] = []
        gray_ap_map: typing.Dict[int, int] = cls.get_gray_ap_map()

        # 更新主机ap id
        for v1_ap_id, v2_ap_id in gray_ap_map.items():

            # 如果为rollback查询v2_ap_id
            query_params: typing.Dict = {"bk_biz_id__in": bk_biz_ids, "ap_id": v2_ap_id if rollback else v1_ap_id}

            # 非业务整体灰度时，需要添加主机范围限制
            if not is_biz_gray:
                # 增加管控区域主机查询参数
                query_params.update(bk_host_id__in=host_ids)

            partial_host_nodes: typing.List[typing.Dict[str, int]] = list(
                node_man_models.Host.objects.filter(**query_params).values("bk_host_id", "bk_biz_id")
            )

            # 切换接入点
            update_kwargs: typing.Dict[str, typing.Any] = {"updated_at": timezone.now()}
            partial_host_ids: typing.List[int] = [host_node["bk_host_id"] for host_node in partial_host_nodes]
            gse_v1_ap_id_is_none_host_count: int = 0
            # 若需要更新gse_v1_ap_id使用F方式,顺序不可以变
            if rollback:
                # 先更新gse_v1_ap_id 为None的主机更新成映射对应的v1_ap_id(需要保证映射为一对一关系)
                gse_v1_ap_id_is_none_host_ids: typing.List[int] = list(
                    node_man_models.Host.objects.filter(
                        bk_biz_id__in=bk_biz_ids,
                        bk_host_id__in=partial_host_ids,
                        gse_v1_ap_id=None,
                    ).values_list("bk_host_id", flat=True)
                )

                gse_v1_ap_id_is_none_host_count: int = node_man_models.Host.objects.filter(
                    bk_host_id__in=gse_v1_ap_id_is_none_host_ids
                ).update(ap_id=v1_ap_id)

                logger.info(
                    f"[update_host_ap_by_host_ids][rollback={rollback}] "
                    f"gse_v1_ap_id_is_none_host_ids -> {gse_v1_ap_id_is_none_host_ids}, "
                    f"Replacement AP ID -> {v1_ap_id}"
                )

                need_update_host_ids: typing.List[int] = list(
                    set(partial_host_ids) - set(gse_v1_ap_id_is_none_host_ids)
                )

                # 更新gse_v1_ap_id不为None的主机
                update_kwargs.update(
                    ap_id=F("gse_v1_ap_id"),
                    gse_v1_ap_id=None,
                )
            else:
                update_kwargs.update(
                    gse_v1_ap_id=F("ap_id"),
                    ap_id=v2_ap_id,
                )
                need_update_host_ids: typing.List[int] = partial_host_ids

            update_count: int = node_man_models.Host.objects.filter(
                bk_biz_id__in=bk_biz_ids, bk_host_id__in=need_update_host_ids
            ).update(**update_kwargs)

            update_count: int = update_count + gse_v1_ap_id_is_none_host_count
            if all(
                [
                    update_count,
                    not is_biz_gray,
                    rollback,
                ]
            ):
                # 如果按业务回滚在上层已进行了回滚，此处不做处理
                # 将与回滚主机关联的业务和管控区域回滚
                rollback_host_infos: typing.List[typing.Dict[str, int]] = list(
                    node_man_models.Host.objects.filter(bk_host_id__in=partial_host_ids)
                    .values("bk_biz_id", "bk_cloud_id")
                    .distinct()
                    .order_by("bk_biz_id")
                )

                bk_biz_ids: typing.Set[int] = set()
                bk_cloud_ids: typing.Set[int] = set()
                for host_info in rollback_host_infos:
                    bk_biz_ids.add(host_info["bk_biz_id"])
                    bk_cloud_ids.add(host_info["bk_cloud_id"])

                logger.info(
                    f"[update_host_ap_by_host_ids][rollback={rollback}] "
                    f"bk_biz_ids -> {bk_biz_ids}, bk_cloud_ids -> {bk_cloud_ids}"
                )

                cls.update_cloud_ap_id(
                    validated_data={"bk_biz_ids": bk_biz_ids}, cloud_ids=list(bk_cloud_ids), rollback=True
                )
                cls.update_gray_scope_list(validated_data={"bk_biz_ids": bk_biz_ids}, rollback=True)

            logger.info(
                f"[update_host_ap_by_host_ids][rollback={rollback}] "
                f"Update count -> {update_count}, "
                f"expect count -> {len(partial_host_nodes)}"
            )

            # 聚合需要操作的主机节点
            host_nodes.extend(partial_host_nodes)

        return {"host_nodes": host_nodes}

    @classmethod
    def update_host_ap(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]], is_biz_gray: bool, rollback: bool = False
    ) -> typing.Dict[str, typing.Any]:

        clouds_ip_host_ids: typing.List[int] = cls.get_cloud_host_query_params(validated_data)

        return cls.update_host_ap_by_host_ids(clouds_ip_host_ids, validated_data["bk_biz_ids"], is_biz_gray, rollback)

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
            node_man_models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, list(set(gray_scope_list))
        )
        logger.info(f"[update_gray_scope_list][rollback={rollback}] commit to db")

        # 触发一次缓存主动更新
        GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False)
        logger.info("[update_gray_scope_list][rollback={rollback}] flush cache")

    @classmethod
    def update_cloud_ap_id(
        cls,
        validated_data: typing.Dict[str, typing.List[typing.Any]],
        cloud_ids: typing.Optional[typing.List[int]] = None,
        rollback: bool = False,
    ):
        gray_ap_map: typing.Dict[int, int] = cls.get_gray_ap_map()
        gray_scope_list: typing.List[int] = GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False)

        cloud_ids: typing.List[int] = cloud_ids or list(
            set(
                node_man_models.Host.objects.filter(bk_biz_id__in=validated_data["bk_biz_ids"]).values_list(
                    "bk_cloud_id", flat=True
                )
            )
        )

        ap_id_obj_map: typing.Dict[int, node_man_models.AccessPoint] = node_man_models.AccessPoint.ap_id_obj_map()

        for cloud_id in cloud_ids:
            cloud_obj: typing.Optional[node_man_models.Cloud] = node_man_models.Cloud.objects.filter(
                bk_cloud_id=cloud_id
            ).first()

            # 跳过管控区域不存在的情况
            if not cloud_obj:
                continue

            cloud_bk_biz_ids: typing.List[int] = list(
                set(node_man_models.Host.objects.filter(bk_cloud_id=cloud_id).values_list("bk_biz_id", flat=True))
            )

            if ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V2.value and rollback:
                # 当管控区域覆盖的业务（cloud_bk_biz_ids）完全包含于灰度业务集（gray_scope_list）时，需要操作回滚
                if not set(cloud_bk_biz_ids) - set(gray_scope_list):
                    logger.info(
                        f"update_cloud_ap_id[rollback]: bk_cloud_id -> {cloud_obj.bk_cloud_id}",
                        f"cloud_ap_id -> {cloud_obj.ap_id}, gse_v1_ap_id -> {cloud_obj.gse_v1_ap_id}",
                    )
                    cloud_obj.ap_id = cloud_obj.gse_v1_ap_id
                    cloud_obj.gse_v1_ap_id = None
                    cloud_obj.save()
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V1.value and rollback:
                # 回滚情况且管控区域接入点版本为V1不需处理
                continue
            elif ap_id_obj_map[cloud_obj.ap_id].gse_version == GseVersion.V2.value:
                # 非rollback且管控区域接入点版本为V2不需处理
                continue
            else:
                # 当管控区域覆盖的业务（cloud_bk_biz_ids）完全包含于灰度业务集（gray_scope_list）时，需要操作灰度
                if not set(cloud_bk_biz_ids) - set(gray_scope_list):
                    try:
                        # 记录v1 ap_id用于回滚
                        cloud_obj.gse_v1_ap_id = cloud_obj.ap_id
                        cloud_obj.ap_id = gray_ap_map[cloud_obj.ap_id]
                        cloud_obj.save()
                    except KeyError:
                        raise ApiError(
                            _("缺少「管控区域」 -> {bk_cloud_name} ID -> {bk_cloud_id}, 接入点版本的映射关系，请联系管理员").format(
                                bk_cloud_name=cloud_obj.bk_cloud_name, bk_cloud_id=cloud_obj.bk_cloud_id
                            )
                        )

    @classmethod
    def is_biz_gray(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):
        return "cloud_ips" not in validated_data

    @classmethod
    def build(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):

        # 不传 cloud_ips 表示按业务灰度
        is_biz_gray: bool = cls.is_biz_gray(validated_data)

        with atomic():
            if is_biz_gray:
                # 更新灰度业务范围
                cls.update_gray_scope_list(validated_data)

                # 更新管控区域接点
                cls.update_cloud_ap_id(validated_data)

            # 更新主机ap
            update_result: typing.Dict[str, typing.Any] = cls.update_host_ap(validated_data, is_biz_gray)

        return cls.activate(update_result["host_nodes"], rollback=False, only_status=False)

    @classmethod
    def rollback(cls, validated_data: typing.Dict[str, typing.List[typing.Any]]):

        # 不传 cloud_ips 表示按业务灰度
        is_biz_gray: bool = cls.is_biz_gray(validated_data)

        with atomic():
            if is_biz_gray:
                # 需要先回滚管控区域，确保业务移除灰度列表前能正常判定管控区域所属关系
                # 更新管控区域接入点
                cls.update_cloud_ap_id(validated_data, rollback=True)

                # 更新灰度业务范围, 无论是按业务还是ip回滚都去掉业务灰度标记
                cls.update_gray_scope_list(validated_data, rollback=True)

            # 更新主机ap
            update_result: typing.Dict[str, typing.Any] = cls.update_host_ap(validated_data, is_biz_gray, rollback=True)

        return cls.activate(update_result["host_nodes"], rollback=True, only_status=False)

    @classmethod
    def list_biz_ids(cls) -> typing.Set[int]:
        """
        获取灰度业务id列表
        """
        return set(GrayTools.get_or_create_gse2_gray_scope_list(get_cache=False))

    @classmethod
    def generate_upgrade_to_agent_id_request_params(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False
    ) -> typing.Dict[str, typing.Any]:

        is_biz_gray: bool = cls.is_biz_gray(validated_data)
        if is_biz_gray:
            host_query_params: typing.Dict[str, typing.List[int]] = {"bk_biz_id__in": validated_data["bk_biz_ids"]}
        else:
            clouds_ip_host_ids: typing.List[int] = cls.get_cloud_host_query_params(validated_data)
            host_query_params: typing.Dict[str, typing.List[int]] = {"bk_host_id__in": clouds_ip_host_ids}

        logger.info(f"[upgrade_or_rollback_agent_id][rollback={rollback}] host_query_params -> {host_query_params}")

        # 生成更新或回滚请求参数
        hosts: typing.List[node_man_models.Host] = node_man_models.Host.objects.filter(**host_query_params).only(
            "inner_ip",
            "bk_cloud_id",
            "bk_agent_id",
        )
        request_hosts: typing.List[typing.Dict[str, typing.Any]] = []
        no_bk_agent_id_hosts: typing.List[str] = []
        for host in hosts:
            if not rollback and not host.bk_agent_id:
                # rollback == false 需要过滤掉bk_agent_id为空的情况
                no_bk_agent_id_hosts.append(f"{host.bk_cloud_id}:{host.inner_ip}")
            else:
                request_hosts.append(
                    {
                        "ip": host.inner_ip,
                        "bk_cloud_id": host.bk_cloud_id,
                        "bk_agent_id": [host.bk_agent_id, f"{host.bk_cloud_id}:{host.inner_ip}"][rollback],
                    }
                )

        return {
            "request_hosts": request_hosts,
            "no_bk_agent_id_hosts": no_bk_agent_id_hosts,
        }

    @classmethod
    def upgrade_or_rollback_agent_id(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]], rollback: bool = False
    ) -> typing.Dict[str, typing.List[typing.List[str]]]:
        request_params: typing.Dict[str, typing.Any] = cls.generate_upgrade_to_agent_id_request_params(
            validated_data=validated_data, rollback=rollback
        )

        # 请求GSE接口更新AgentID配置
        result: typing.Dict[str, typing.List[typing.Any]] = {
            "no_bk_agent_id_hosts": request_params["no_bk_agent_id_hosts"]
        }
        result.update(**get_gse_api_helper(GseVersion.V2.value).upgrade_to_agent_id(request_params["request_hosts"]))
        return result

    @classmethod
    def upgrade_to_agent_id(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]]
    ) -> typing.Dict[str, typing.List[typing.List[str]]]:
        return cls.upgrade_or_rollback_agent_id(validated_data)

    @classmethod
    def rollback_agent_id(
        cls, validated_data: typing.Dict[str, typing.List[typing.Any]]
    ) -> typing.Dict[str, typing.List[typing.List[str]]]:
        return cls.upgrade_or_rollback_agent_id(validated_data, rollback=True)
