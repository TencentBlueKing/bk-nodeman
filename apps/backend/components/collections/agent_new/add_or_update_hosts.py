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
import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.core.concurrent import controller
from apps.node_man import constants, models, tools
from apps.node_man.models import ProcessStatus
from apps.utils import batch_request, concurrent, exc
from common.api import CCApi

from .. import core
from ..base import CommonData
from .base import AgentBaseService


class SelectorResult:
    is_add: bool = None
    is_skip: bool = None
    sub_inst: models.SubscriptionInstanceRecord = None

    def __init__(self, is_add: bool, is_skip: bool, sub_inst: models.SubscriptionInstanceRecord):
        self.is_add = is_add
        self.is_skip = is_skip
        self.sub_inst = sub_inst


class AddOrUpdateHostsService(AgentBaseService):
    @staticmethod
    def get_host_infos_gby_ip_key(host_infos: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        获取 主机信息根据 IP 等关键信息聚合的结果
        :param host_infos: 主机信息列表
        :return: 主机信息根据 IP 等关键信息聚合的结果
        """
        host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for host_info in host_infos:
            bk_cloud_id: int = host_info["bk_cloud_id"]
            bk_addressing: str = host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value)
            optional_ips: List[Optional[str]] = [host_info.get("bk_host_innerip"), host_info.get("bk_host_innerip_v6")]

            for ip in optional_ips:
                if not ip:
                    continue
                ip_key: str = f"{bk_addressing}:{bk_cloud_id}:{ip}"
                host_infos_gby_ip_key[ip_key].append(host_info)
        return host_infos_gby_ip_key

    @staticmethod
    def search_business(bk_biz_id: int) -> Dict[str, Any]:
        """
        查询相应业务的业务运维
        :param bk_biz_id: 业务ID
        :return: 列表 ，包含 业务ID、名字、业务运维
        """
        if bk_biz_id == settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
            return {
                "bk_biz_maintainer": "",
                "bk_biz_id": bk_biz_id,
                "bk_biz_name": settings.BK_CMDB_RESOURCE_POOL_BIZ_NAME,
            }
        search_business_params = {
            "fields": ["bk_biz_id", "bk_biz_name", "bk_biz_maintainer"],
            "condition": {"bk_biz_id": bk_biz_id},
        }
        return CCApi.search_business(search_business_params)["info"][0]

    def static_ip_selector(
        self, sub_inst: models.SubscriptionInstanceRecord, cmdb_hosts: List[Dict[str, Any]]
    ) -> SelectorResult:
        """
        静态 IP 处理器
        :param sub_inst:
        :param cmdb_hosts:
        :return:
        """
        # 不存在则新增
        if not cmdb_hosts:
            return SelectorResult(is_add=True, is_skip=False, sub_inst=sub_inst)

        # 静态IP情况下，只会存在一台机器
        cmdb_host: Dict[str, Any] = cmdb_hosts[0]
        except_bk_biz_id: int = sub_inst.instance_info["host"]["bk_biz_id"]
        if except_bk_biz_id != cmdb_host["bk_biz_id"]:
            self.move_insts_to_failed(
                sub_inst.id,
                log_content=_("主机期望注册到业务【ID：{except_bk_biz_id}】，但实际存在于业务【ID: {actual_biz_id}】，请前往该业务进行安装").format(
                    except_bk_biz_id=except_bk_biz_id, actual_biz_id=cmdb_host["bk_biz_id"]
                ),
            )
            return SelectorResult(is_add=False, is_skip=True, sub_inst=sub_inst)
        else:
            # 同业务下视为更新
            sub_inst.instance_info["host"]["bk_host_id"] = cmdb_host["bk_host_id"]
            return SelectorResult(is_add=False, is_skip=False, sub_inst=sub_inst)

    def dynamic_ip_selector(
        self, sub_inst: models.SubscriptionInstanceRecord, cmdb_hosts: List[Dict[str, Any]]
    ) -> SelectorResult:
        """
        动态 IP 处理器
        :param sub_inst:
        :param cmdb_hosts:
        :return:
        """
        bk_host_id: Optional[int] = sub_inst.instance_info["host"].get("bk_host_id")
        # 安装场景下主机 ID 不存在，不考虑收敛规则，直接新增
        if bk_host_id is None:
            return SelectorResult(is_add=True, is_skip=False, sub_inst=sub_inst)

        # 查找 bk_host_id 及 所在业务均匹配的主机信息
        cmdb_host_with_the_same_id: Optional[Dict[str, Any]] = None
        except_bk_biz_id: int = sub_inst.instance_info["host"]["bk_biz_id"]
        for cmdb_host in cmdb_hosts:
            if bk_host_id == cmdb_host["bk_host_id"]:
                if except_bk_biz_id == cmdb_host["bk_biz_id"]:
                    cmdb_host_with_the_same_id = cmdb_host
                    break
                else:
                    self.move_insts_to_failed(
                        sub_inst.id,
                        log_content=_(
                            "主机期望注册到业务【ID：{except_bk_biz_id}】，但实际存在于业务【ID: {actual_biz_id}】，请前往该业务进行安装"
                        ).format(except_bk_biz_id=except_bk_biz_id, actual_biz_id=cmdb_host["bk_biz_id"]),
                    )
                    return SelectorResult(is_add=False, is_skip=True, sub_inst=sub_inst)

        if cmdb_host_with_the_same_id:
            # 存在则执行更新逻辑，面向重装场景
            return SelectorResult(is_add=False, is_skip=False, sub_inst=sub_inst)
        return SelectorResult(is_add=True, is_skip=False, sub_inst=sub_inst)

    @controller.ConcurrentController(
        data_list_name="bk_host_ids",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=lambda: {"limit": constants.QUERY_CMDB_LIMIT},
    )
    def find_host_biz_relations(self, bk_host_ids: List[int]) -> List[Dict[str, Any]]:
        """
        查询主机业务关系信息
        :param bk_host_ids: 主机列表
        :return: 主机业务关系列表
        """
        # 接口对于空数组的处理是报错，这里需要提前处理返回
        if not bk_host_ids:
            return []
        return CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids})

    def query_hosts_by_addressing(self, host_infos: List[Dict[str, Any]], bk_addressing: str) -> List[Dict[str, Any]]:
        """
        按寻址方式查询主机
        :param host_infos: 主机信息列表
        :param bk_addressing: 寻址方式
        :return: 主机信息列表
        """
        bk_cloud_id_set: Set[int] = set()
        bk_host_innerip_set: Set[str] = set()
        bk_host_innerip_v6_set: Set[str] = set()

        for host_info in host_infos:
            bk_cloud_id: Optional[int] = host_info.get("bk_cloud_id")
            # IPv6 / IPv6 可能存在其中一个为空的现象
            bk_host_innerip: Optional[str] = host_info.get("bk_host_innerip")
            bk_host_innerip_v6: Optional[str] = host_info.get("bk_host_innerip_v6")

            if bk_cloud_id is not None:
                bk_cloud_id_set.add(bk_cloud_id)
            if bk_host_innerip:
                bk_host_innerip_set.add(bk_host_innerip)
            if bk_host_innerip_v6:
                bk_host_innerip_v6_set.add(bk_host_innerip_v6)

        query_hosts_params: Dict[str, Any] = {
            "fields": constants.CC_HOST_FIELDS,
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_addressing", "operator": "equal", "value": bk_addressing},
                    {"field": "bk_cloud_id", "operator": "in", "value": list(bk_cloud_id_set)},
                    {
                        "condition": "OR",
                        "rules": [
                            {"field": "bk_host_innerip", "operator": "in", "value": list(bk_host_innerip_set)},
                            {"field": "bk_host_innerip_v6", "operator": "in", "value": list(bk_host_innerip_v6_set)},
                        ],
                    },
                ],
            },
        }
        cmdb_host_infos: List[Dict[str, Any]] = batch_request.batch_request(
            func=CCApi.list_hosts_without_biz, params=query_hosts_params
        )

        processed_cmdb_host_infos: List[Dict[str, Any]] = []
        host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = self.get_host_infos_gby_ip_key(host_infos)
        cmdb_host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = self.get_host_infos_gby_ip_key(cmdb_host_infos)
        # 模糊查询所得的主机信息列表可能出现：同 IP + 不同管控区域的冗余主机
        # 仅选择原数据中存在的 IP + 管控区域组合
        for ip_key, partial_cmdb_host_infos in cmdb_host_infos_gby_ip_key.items():
            if not host_infos_gby_ip_key.get(ip_key):
                continue
            processed_cmdb_host_infos.extend(partial_cmdb_host_infos)
        # 数据按 IP 协议版本进行再聚合，同时存在 v4/v6 的情况下会生成重复项，需要按 主机ID 去重
        processed_cmdb_host_infos = tools.HostV2Tools.host_infos_deduplication(processed_cmdb_host_infos)
        return processed_cmdb_host_infos

    def query_hosts(self, sub_insts: List[models.SubscriptionInstanceRecord]) -> List[Dict[str, Any]]:
        """
        查询主机信息
        :param sub_insts: 订阅实例
        :return: 主机信息列表
        """
        host_infos_gby_addressing: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for sub_inst in sub_insts:
            host_info: Dict[str, Any] = sub_inst.instance_info["host"]
            bk_addressing: str = host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value)
            host_infos_gby_addressing[bk_addressing].append(host_info)

        query_hosts_params_list: List[Dict[str, Any]] = []
        for addressing, host_infos in host_infos_gby_addressing.items():
            query_hosts_params_list.append({"host_infos": host_infos, "bk_addressing": addressing})

        cmdb_hosts: List[Dict] = concurrent.batch_call(
            func=self.query_hosts_by_addressing, params_list=query_hosts_params_list, extend_result=True
        )

        bk_host_ids: List[int] = [cmdb_host["bk_host_id"] for cmdb_host in cmdb_hosts]
        host_biz_relations: List[Dict[str, Any]] = self.find_host_biz_relations(bk_host_ids=bk_host_ids)
        host_id__relation_map: Dict[int, Dict[str, Any]] = {
            host_biz_relation["bk_host_id"]: host_biz_relation for host_biz_relation in host_biz_relations
        }

        # 主机信息填充业务关系
        for cmdb_host in cmdb_hosts:
            cmdb_host.update(host_id__relation_map.get(cmdb_host["bk_host_id"], {}))

        return cmdb_hosts

    @controller.ConcurrentController(
        data_list_name="sub_insts",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.HOST_WRITE.value},
    )
    @exc.ExceptionHandler(exc_handler=core.default_sub_insts_task_exc_handler)
    def handle_update_cmdb_hosts_case(self, sub_insts: List[models.SubscriptionInstanceRecord]) -> List[int]:
        """
        批量更新 CMDB 主机
        :param sub_insts: 订阅实例列表
        :return: 返回成功更新的订阅实例 ID 列表
        """
        if not sub_insts:
            return []

        sub_inst_ids: List[int] = []
        update_list: List[Dict[str, Any]] = []
        for sub_inst in sub_insts:
            sub_inst_ids.append(sub_inst.id)
            sub_inst.update_time = timezone.now()
            host_info: Dict[str, Any] = sub_inst.instance_info["host"]
            update_params: Dict[str, Any] = {
                "bk_host_id": host_info["bk_host_id"],
                "properties": {
                    "bk_cloud_id": host_info["bk_cloud_id"],
                    "bk_addressing": host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value),
                    "bk_host_innerip": host_info.get("bk_host_innerip", ""),
                    "bk_host_innerip_v6": host_info.get("bk_host_innerip_v6", ""),
                    "bk_host_outerip": host_info.get("bk_host_outerip", ""),
                    "bk_host_outerip_v6": host_info.get("bk_host_outerip_v6", ""),
                    "bk_os_type": constants.BK_OS_TYPE[host_info["os_type"]],
                },
            }
            self.log_info(
                sub_inst_ids=sub_inst.id,
                log_content=_("更新 CMDB 主机信息:\n {params}").format(params=json.dumps(update_params, indent=2)),
            )
            update_list.append(update_params)
        CCApi.batch_update_host({"update": update_list})
        models.SubscriptionInstanceRecord.objects.bulk_update(
            sub_insts, fields=["instance_info", "update_time"], batch_size=self.batch_size
        )
        return sub_inst_ids

    @controller.ConcurrentController(
        data_list_name="sub_insts",
        batch_call_func=concurrent.batch_call,
        get_config_dict_func=core.get_config_dict,
        get_config_dict_kwargs={"config_name": core.ServiceCCConfigName.HOST_WRITE.value},
    )
    @exc.ExceptionHandler(exc_handler=core.default_sub_insts_task_exc_handler)
    def add_host_to_business_idle(self, biz_info: Dict[str, Any], sub_insts: List[models.SubscriptionInstanceRecord]):
        sub_inst_ids: List[int] = []
        bk_host_list: List[Dict[str, Any]] = []
        for sub_inst in sub_insts:
            sub_inst_ids.append(sub_inst.id)
            host_info: Dict[str, Any] = sub_inst.instance_info["host"]
            register_params: Dict[str, Any] = {
                # "3" 表示API导入
                "import_from": "3",
                "bk_cloud_id": host_info["bk_cloud_id"],
                "bk_addressing": host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value),
                "bk_host_innerip": host_info.get("bk_host_innerip", ""),
                "bk_host_innerip_v6": host_info.get("bk_host_innerip_v6", ""),
                "bk_host_outerip": host_info.get("bk_host_outerip", ""),
                "bk_host_outerip_v6": host_info.get("bk_host_outerip_v6", ""),
                "bk_os_type": constants.BK_OS_TYPE[host_info["os_type"]],
                "bk_bak_operator": biz_info.get("bk_biz_maintainer") or host_info.get("username"),
                "operator": biz_info.get("bk_biz_maintainer") or host_info.get("username"),
            }
            self.log_info(
                sub_inst_ids=sub_inst.id,
                log_content=_("添加主机到业务 {bk_biz_name}[{bk_biz_id}]:\n {params}").format(
                    bk_biz_name=biz_info["bk_biz_name"],
                    bk_biz_id=biz_info["bk_biz_id"],
                    params=json.dumps(register_params, indent=2),
                ),
            )
            bk_host_list.append(register_params)
        bk_host_ids: List[int] = CCApi.add_host_to_business_idle(
            {"bk_biz_id": biz_info["bk_biz_id"], "bk_host_list": bk_host_list}
        )["bk_host_ids"]
        # 新增主机是一个原子性操作，返回的 ID 列表会按索引顺序对应
        for bk_host_id, sub_inst in zip(bk_host_ids, sub_insts):
            sub_inst.update_time = timezone.now()
            sub_inst.instance_info["host"]["bk_host_id"] = bk_host_id
        # 更新订阅实例中的实例信息
        models.SubscriptionInstanceRecord.objects.bulk_update(
            sub_insts, fields=["instance_info", "update_time"], batch_size=self.batch_size
        )
        return sub_inst_ids

    def handle_add_cmdb_hosts_case(self, sub_insts: List[models.SubscriptionInstanceRecord]) -> List[int]:
        """
        批量添加主机到 CMDB
        :param sub_insts: 订阅实例列表
        :return: 返回成功的订阅实例 ID 列表
        """
        if not sub_insts:
            return []

        sub_insts_gby_biz_id: Dict[int, List[models.SubscriptionInstanceRecord]] = defaultdict(list)
        for sub_inst in sub_insts:
            bk_biz_id: int = sub_inst.instance_info["host"]["bk_biz_id"]
            sub_insts_gby_biz_id[bk_biz_id].append(sub_inst)

        params_list: List[Dict[str, Any]] = []
        for bk_biz_id, partial_sub_insts in sub_insts_gby_biz_id.items():
            biz_info: Dict[str, Any] = self.search_business(bk_biz_id)
            params_list.append({"biz_info": biz_info, "sub_insts": partial_sub_insts})

        return concurrent.batch_call(func=self.add_host_to_business_idle, params_list=params_list, extend_result=True)

    @transaction.atomic
    def handle_update_db(self, sub_insts: List[models.SubscriptionInstanceRecord]):
        """
        :param sub_insts: 订阅实例列表
        :return:
        """
        # 为空时无需更新，减少无效IO
        if not sub_insts:
            return
        bk_host_ids: List[int] = []
        for sub_inst in sub_insts:
            bk_host_ids.append(sub_inst.instance_info["host"]["bk_host_id"])

        host_ids_in_exist_hosts: Set[int] = set(
            models.Host.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True)
        )
        host_ids_in_exist_proc_statuses: Set[int] = set(
            models.ProcessStatus.objects.filter(
                bk_host_id__in=bk_host_ids,
                name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
            ).values_list("bk_host_id", flat=True)
        )
        host_objs_to_be_created: List[models.Host] = []
        host_objs_to_be_updated: List[models.Host] = []
        proc_status_objs_to_be_created: List[models.ProcessStatus] = []
        for sub_inst in sub_insts:

            host_info: Dict[str, Any] = sub_inst.instance_info["host"]

            bk_host_id: int = host_info["bk_host_id"]
            inner_ip: str = host_info.get("bk_host_innerip") or ""
            inner_ipv6: str = host_info.get("bk_host_innerip_v6") or ""
            outer_ip: str = host_info.get("bk_host_outerip") or ""
            outer_ipv6: str = host_info.get("bk_host_outerip_v6") or ""
            login_ip: str = host_info.get("login_ip") or ""

            if host_info["host_node_type"] == constants.NodeType.PROXY:
                # Proxy login_ip 为空的情况取值顺序：外网 IP（v4 -> v6）-> 内网 IP（v4 -> v6）
                login_ip = login_ip or outer_ip or outer_ipv6 or inner_ip or inner_ipv6
            else:
                # 其他情况下：内网 IP（v4 -> v6）
                login_ip = login_ip or inner_ip or inner_ipv6

            extra_data = {
                "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
                "bt_speed_limit": host_info.get("bt_speed_limit", 0),
                "enable_compression": host_info.get("enable_compression", False),
            }
            if host_info.get("data_path"):
                extra_data.update({"data_path": host_info.get("data_path")})
            host_obj = models.Host(
                bk_host_id=bk_host_id,
                bk_cloud_id=host_info["bk_cloud_id"],
                bk_addressing=host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value),
                bk_biz_id=host_info["bk_biz_id"],
                inner_ip=inner_ip,
                inner_ipv6=inner_ipv6,
                outer_ip=outer_ip,
                outer_ipv6=outer_ipv6,
                login_ip=login_ip,
                data_ip=host_info.get("data_ip") or "",
                is_manual=host_info.get("is_manual", False),
                os_type=host_info["os_type"],
                node_type=host_info["host_node_type"],
                ap_id=host_info["ap_id"],
                install_channel_id=host_info.get("install_channel_id"),
                upstream_nodes=host_info.get("upstream_nodes", []),
                updated_at=timezone.now(),
                extra_data=extra_data,
            )
            if bk_host_id in host_ids_in_exist_hosts:
                host_objs_to_be_updated.append(host_obj)
            else:
                # 初次创建主机时，初始化CPU架构，根据操作系统设置默认值，后续通过安装上报日志修正
                host_obj.cpu_arch = (constants.CpuType.x86_64, constants.CpuType.powerpc)[
                    host_obj.cpu_arch == constants.OsType.AIX
                ]
                host_objs_to_be_created.append(host_obj)

            if bk_host_id not in host_ids_in_exist_proc_statuses:
                proc_status_obj = models.ProcessStatus(
                    bk_host_id=bk_host_id,
                    source_type=ProcessStatus.SourceType.DEFAULT,
                    status=constants.ProcStateType.NOT_INSTALLED,
                    name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                )
                proc_status_objs_to_be_created.append(proc_status_obj)

        models.Host.objects.bulk_create(host_objs_to_be_created, batch_size=self.batch_size)
        models.Host.objects.bulk_update(
            host_objs_to_be_updated,
            fields=["bk_biz_id", "bk_cloud_id", "bk_addressing", "os_type", "node_type"]
            + ["inner_ip", "inner_ipv6", "outer_ip", "outer_ipv6", "login_ip", "data_ip"]
            + ["is_manual", "ap_id", "install_channel_id", "upstream_nodes", "updated_at", "extra_data"],
            batch_size=self.batch_size,
        )
        models.ProcessStatus.objects.bulk_create(proc_status_objs_to_be_created, batch_size=self.batch_size)

    def _execute(self, data, parent_data, common_data: CommonData):
        subscription_instances: List[models.SubscriptionInstanceRecord] = common_data.subscription_instances

        sub_insts_to_be_added: List[models.SubscriptionInstanceRecord] = []
        sub_insts_to_be_updated: List[models.SubscriptionInstanceRecord] = []
        id__sub_inst_obj_map: Dict[int, models.SubscriptionInstanceRecord] = {}
        # 获取已存在于 CMDB 的主机信息
        exist_cmdb_hosts: List[Dict[str, Any]] = self.query_hosts(subscription_instances)
        # 按 IpKey 聚合主机信息
        # IpKey：ip（v4 or v6）+ bk_addressing（寻值方式）+ bk_cloud_id（管控区域）
        cmdb_host_infos_gby_ip_key: Dict[str, List[Dict[str, Any]]] = self.get_host_infos_gby_ip_key(exist_cmdb_hosts)
        for sub_inst in subscription_instances:
            id__sub_inst_obj_map[sub_inst.id] = sub_inst
            host_info: Dict[str, Any] = sub_inst.instance_info["host"]
            bk_addressing: str = host_info.get("bk_addressing", constants.CmdbAddressingType.STATIC.value)

            # 获取已存在于 CMDB，且 ip_field_names 对应值所构建的 IpKey 相同的主机信息
            cmdb_hosts_with_the_same_ips: List[Dict[str, Any]] = tools.HostV2Tools.get_host_infos_with_the_same_ips(
                host_infos_gby_ip_key=cmdb_host_infos_gby_ip_key,
                host_info=host_info,
                ip_field_names=["bk_host_innerip", "bk_host_innerip_v6"],
            )

            # 按照寻址方式通过不同的选择器，选择更新或新增主机到 CMDB
            if bk_addressing == constants.CmdbAddressingType.DYNAMIC.value:
                selector_result: SelectorResult = self.dynamic_ip_selector(sub_inst, cmdb_hosts_with_the_same_ips)
            else:
                selector_result: SelectorResult = self.static_ip_selector(sub_inst, cmdb_hosts_with_the_same_ips)

            if selector_result.is_skip:
                # 选择器已处理，跳过
                continue
            elif selector_result.is_add:
                sub_insts_to_be_added.append(selector_result.sub_inst)
            else:
                sub_insts_to_be_updated.append(selector_result.sub_inst)

        # 1 - 新增或更新 CMDB 主机
        successfully_added_sub_inst_ids: List[int] = self.handle_add_cmdb_hosts_case(sub_insts=sub_insts_to_be_added)
        successfully_updated_sub_inst_ids: List[int] = self.handle_update_cmdb_hosts_case(
            sub_insts=sub_insts_to_be_updated
        )

        # 2 - 对操作成功的实例更新本地数据
        succeed_sub_insts: List[models.SubscriptionInstanceRecord] = []
        for sub_inst_id in successfully_added_sub_inst_ids + successfully_updated_sub_inst_ids:
            succeed_sub_insts.append(id__sub_inst_obj_map[sub_inst_id])
        self.handle_update_db(succeed_sub_insts)
