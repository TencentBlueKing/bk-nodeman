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
import base64
import json
from collections import ChainMap, defaultdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Set

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.backend.subscription import tools
from apps.component.esbclient import client_v2
from apps.node_man import constants, models
from apps.node_man.models import ProcessStatus
from apps.utils import basic, batch_request, concurrent

from .base import AgentBaseService, AgentCommonData


class RegisterHostService(AgentBaseService):
    @classmethod
    def fetch_sub_inst_ids_by_host_keys(
        cls, host_keys: Iterable[str], host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord]
    ) -> Set[int]:
        sub_inst_ids: Set[int] = set()
        for host_key in host_keys:
            sub_inst = host_key__sub_inst_map.get(host_key)
            if not sub_inst:
                continue
            sub_inst_ids.add(sub_inst.id)
        return sub_inst_ids

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
        return client_v2.cc.search_business(search_business_params)["info"][0]

    @classmethod
    def query_cmdb_hosts_and_structure(
        cls,
        host_keys: Iterable[str],
        cmdb_query_api_func: Callable,
        host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord],
        bk_biz_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        通过CMDB查询主机
        :param host_keys: 主机唯一标识集合
        :param cmdb_query_api_func: cmdb查询接口
        :param host_key__sub_inst_map: host_key - 订阅实例映射
        :param bk_biz_id: 业务ID
        :return:
        """
        bk_cloud_ids: Set[int] = set()
        bk_host_innerips: List[str] = []
        host_keys: Set[str] = set(host_keys)
        for host_key in host_keys:
            bk_cloud_ids.add(host_key__sub_inst_map[host_key].instance_info["host"]["bk_cloud_id"])
            bk_host_innerips.append(host_key__sub_inst_map[host_key].instance_info["host"]["bk_host_innerip"])

        list_cmdb_hosts_params = {
            "bk_biz_id": bk_biz_id,
            "fields": ["bk_host_id", "bk_host_innerip", "bk_cloud_id"],
            "host_property_filter": {
                "condition": "AND",
                "rules": [
                    {"field": "bk_cloud_id", "operator": "in", "value": list(bk_cloud_ids)},
                    {"field": "bk_host_innerip", "operator": "in", "value": list(bk_host_innerips)},
                ],
            },
        }
        if cmdb_query_api_func == client_v2.cc.list_hosts_without_biz:
            list_cmdb_hosts_params.pop("bk_biz_id")

        cmdb_host_infos: List[Dict[str, Any]] = batch_request.batch_request(
            func=cmdb_query_api_func, params=list_cmdb_hosts_params
        )

        host_keys_in_cmdb: Set[str] = set()
        bk_host_ids: List[int] = []
        host_key__bk_host_id_map: Dict[str, int] = {}
        bk_host_id__host_key_map: Dict[int, str] = {}
        for cmdb_host_info in cmdb_host_infos:
            host_key = f"{cmdb_host_info['bk_cloud_id']}-{cmdb_host_info['bk_host_innerip']}"
            # 过滤查出的多余主机
            if host_key not in host_keys:
                continue
            host_keys_in_cmdb.add(host_key)
            bk_host_ids.append(cmdb_host_info["bk_host_id"])
            host_key__bk_host_id_map[host_key] = cmdb_host_info["bk_host_id"]
            bk_host_id__host_key_map[cmdb_host_info["bk_host_id"]] = host_key

        return {
            "cmdb_host_infos": cmdb_host_infos,
            "host_keys_in_cmdb": host_keys_in_cmdb,
            "bk_host_ids": bk_host_ids,
            "bk_host_id__host_key_map": bk_host_id__host_key_map,
            "host_key__bk_host_id_map": host_key__bk_host_id_map,
        }

    def add_hosts_to_biz_thread(
        self,
        biz_info: Dict[str, Any],
        host_info_chunk_list: List[Dict[str, Any]],
        host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord],
    ) -> List[str]:
        """
        添加主机到CMDB
        :param biz_info: 业务信息
        :param host_info_chunk_list: 待注册的主机信息
        :param host_key__sub_inst_map:
        :return: 成功注册的host keys
        """
        add_host_to_resource_params = {"host_info": {}}
        # 资源池业务无需传入bk_biz_id
        if biz_info["bk_biz_id"] != settings.BK_CMDB_RESOURCE_POOL_BIZ_ID:
            add_host_to_resource_params["bk_biz_id"] = biz_info["bk_biz_id"]

        host_keys: List[str] = []
        sub_inst_ids: Set[int] = set()
        for index, host_info in enumerate(host_info_chunk_list):
            host_key = f"{host_info['bk_cloud_id']}-{host_info['bk_host_innerip']}"
            register_params = {
                index: {
                    "bk_host_innerip": host_info["bk_host_innerip"],
                    # "3" 表示API导入
                    "import_from": "3",
                    "bk_cloud_id": host_info["bk_cloud_id"],
                    "bk_host_outerip": host_info.get("bk_host_outerip", ""),
                    "bk_os_type": constants.BK_OS_TYPE[host_info["os_type"]],
                    "bk_bak_operator": biz_info.get("bk_biz_maintainer") or host_info.get("username"),
                    "operator": biz_info.get("bk_biz_maintainer") or host_info.get("username"),
                }
            }
            host_keys.append(host_key)
            sub_inst_ids.add(host_key__sub_inst_map[host_key].id)
            add_host_to_resource_params["host_info"].update(register_params)
            self.log_info(
                sub_inst_ids=host_key__sub_inst_map[host_key].id,
                log_content=_("注册主机参数为:\n {params}").format(params=json.dumps(register_params, indent=2)),
            )

        add_host_to_resource_result: Dict = client_v2.cc.add_host_to_resource(add_host_to_resource_params)
        error_msgs: List[str] = add_host_to_resource_result.get("error")
        if error_msgs:
            # 对CMDB而言，批量添加主机具有原子性
            self.move_insts_to_failed(
                sub_inst_ids=sub_inst_ids,
                log_content=_("注册主机失败：\n{error_msgs}").format(error_msgs="\n".join(error_msgs)),
            )
            return []
        return host_keys

    def add_hosts_to_biz_resource(
        self,
        bk_biz_id: int,
        host_infos: List[Dict[str, Any]],
        host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord],
    ) -> Dict[str, int]:
        """
        添加主机到业务资源池
        :param bk_biz_id: 业务ID
        :param host_infos: 主机列表
        :param host_key__sub_inst_map:
        :return: 添加到CMDB成功的 host key
        """

        biz_info = self.search_business(bk_biz_id=bk_biz_id)
        add_hosts_to_biz_thread_params_list: List[Dict[str, Any]] = []
        # CMDB 添加主机接口支持批量但具备原子性，每一批的数量不能过多，不然可能会出现单台主机校验失败导致整个安装任务失败
        for host_info_chunk_list in basic.chunk_lists(host_infos, 50):
            add_hosts_to_biz_thread_params_list.append(
                {
                    "biz_info": biz_info,
                    "host_info_chunk_list": host_info_chunk_list,
                    "host_key__sub_inst_map": host_key__sub_inst_map,
                }
            )

        host_keys_try_to_add: List[str] = concurrent.batch_call(
            func=self.add_hosts_to_biz_thread,
            params_list=add_hosts_to_biz_thread_params_list,
            get_data=lambda x: x,
            extend_result=True,
        )
        host_keys_try_to_add: Set[str] = set(host_keys_try_to_add)

        hosts_struct_in_except_cmdb_biz = self.query_cmdb_hosts_and_structure(
            bk_biz_id=bk_biz_id,
            host_keys=host_keys_try_to_add,
            cmdb_query_api_func=client_v2.cc.list_biz_hosts,
            host_key__sub_inst_map=host_key__sub_inst_map,
        )

        # 不存于当前业务的主机，通过无业务接口再查询一次
        host_keys_not_in_except_biz: Set[str] = (
            host_keys_try_to_add - hosts_struct_in_except_cmdb_biz["host_keys_in_cmdb"]
        )
        hosts_struct_in_other_biz = self.query_cmdb_hosts_and_structure(
            host_keys=host_keys_not_in_except_biz,
            cmdb_query_api_func=client_v2.cc.list_hosts_without_biz,
            host_key__sub_inst_map=host_key__sub_inst_map,
        )

        # 处理注册成功，但在CMDB查询不到数据的情况
        host_keys_not_in_cmdb = host_keys_not_in_except_biz - hosts_struct_in_other_biz["host_keys_in_cmdb"]
        self.move_insts_to_failed(
            sub_inst_ids=self.fetch_sub_inst_ids_by_host_keys(host_keys_not_in_cmdb, host_key__sub_inst_map),
            log_content=_("查询CMDB主机失败，未在CMDB中查询到主机信息"),
        )

        sub_inst_ids_gby_log: Dict[str, List[int]] = defaultdict(list)
        host_biz_relations = tools.find_host_biz_relations(bk_host_ids=hosts_struct_in_other_biz["bk_host_ids"])
        for host_biz_relation in host_biz_relations:
            bk_host_id = host_biz_relation["bk_host_id"]
            host_key = hosts_struct_in_other_biz["bk_host_id__host_key_map"][host_biz_relation["bk_host_id"]]
            log = _("主机期望注册到「{bk_biz_id}」[{bk_biz_name}]，但实际存在于业务「ID: {actual_biz_id}」，请前往该业务进行安装").format(
                host_key=host_key,
                bk_host_id=bk_host_id,
                bk_biz_id=bk_biz_id,
                bk_biz_name=biz_info["bk_biz_name"],
                actual_biz_id=host_biz_relation["bk_biz_id"],
            )
            sub_inst_ids_gby_log[log].append(host_key__sub_inst_map[host_key].id)

        for log, sub_inst_ids in sub_inst_ids_gby_log.items():
            self.move_insts_to_failed(sub_inst_ids=sub_inst_ids, log_content=log)

        success_host_keys = host_keys_try_to_add - host_keys_not_in_except_biz
        return {
            success_host_key: hosts_struct_in_except_cmdb_biz["host_key__bk_host_id_map"][success_host_key]
            for success_host_key in success_host_keys
        }

    def handle_empty_auth_info_case(
        self, subscription_instances: List[models.SubscriptionInstanceRecord]
    ) -> Dict[str, models.SubscriptionInstanceRecord]:
        """
        处理不存在认证信息的情况
        :param subscription_instances: 订阅实例对象列表
        :return: host_key__sub_inst_map 校验通过的「host_key - 订阅实例映射」
        """
        empty_auth_info_sub_inst_ids: List[int] = []
        host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord] = {}
        for subscription_instance in subscription_instances:
            host_info = subscription_instance.instance_info["host"]
            is_manual = host_info.get("is_manual", False)

            # 「第三方拉取密码」或者「手动安装」的场景下无需校验是否存在认证信息
            if not (host_info.get("auth_type") == constants.AuthType.TJJ_PASSWORD or is_manual):
                # 记录不存在认证信息的订阅实例ID，跳过记录
                if not (host_info.get("password") or host_info.get("key")):
                    empty_auth_info_sub_inst_ids.append(subscription_instance.id)
                    continue
            # 通过校验的订阅实例构建host_key - 订阅实例 映射
            host_key__sub_inst_map[f"{host_info['bk_cloud_id']}-{host_info['bk_host_innerip']}"] = subscription_instance

        # 移除不存在认证信息的实例
        self.move_insts_to_failed(
            sub_inst_ids=empty_auth_info_sub_inst_ids, log_content=_("该主机的登录认证信息已被清空，无法重试，请重新发起安装任务")
        )
        return host_key__sub_inst_map

    def handle_add_hosts_to_cmdb_case(
        self, host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord]
    ) -> Dict[str, int]:
        """
        处理添加主机到CMDB的情况
        :param host_key__sub_inst_map:
        :return: success host_key__sub_inst_map
        """

        if not host_key__sub_inst_map:
            return {}

        host_infos_gby_bk_biz_id: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for __, sub_inst in host_key__sub_inst_map.items():
            host_info = sub_inst.instance_info["host"]
            host_infos_gby_bk_biz_id[host_info["bk_biz_id"]].append(host_info)

        add_hosts_to_biz_resource_params_list: List[Dict[str, Any]] = []
        for bk_biz_id, host_infos in host_infos_gby_bk_biz_id.items():
            add_hosts_to_biz_resource_params_list.append(
                {"bk_biz_id": bk_biz_id, "host_infos": host_infos, "host_key__sub_inst_map": host_key__sub_inst_map}
            )

        host_key__bk_host_id_maps: List[Dict[str, int]] = concurrent.batch_call(
            func=self.add_hosts_to_biz_resource, params_list=add_hosts_to_biz_resource_params_list, get_data=lambda x: x
        )
        return dict(ChainMap(*host_key__bk_host_id_maps))

    @transaction.atomic
    def handle_update_db(
        self,
        host_key__bk_host_id_map: Dict[str, int],
        host_key__sub_inst_map: Dict[str, models.SubscriptionInstanceRecord],
    ):
        """
        更新DB中主机关联的数据
        :param host_key__bk_host_id_map:
        :param host_key__sub_inst_map:
        :return:
        """
        # 为空时无需更新，减少无效IO
        if not host_key__bk_host_id_map:
            return

        bk_host_ids = host_key__bk_host_id_map.values()
        host_ids_in_exist_hosts: Set[int] = set(
            models.Host.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True)
        )
        host_ids_in_exist_identity_data: Set[int] = set(
            models.IdentityData.objects.filter(bk_host_id__in=bk_host_ids).values_list("bk_host_id", flat=True)
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
        identity_data_objs_to_be_created: List[models.IdentityData] = []
        identity_data_objs_to_be_updated: List[models.IdentityData] = []
        sub_inst_objs_to_be_updated: List[models.SubscriptionInstanceRecord] = []
        for host_key, bk_host_id in host_key__bk_host_id_map.items():

            sub_inst_obj = host_key__sub_inst_map[host_key]
            host_info = sub_inst_obj.instance_info["host"]

            inner_ip = host_info["bk_host_innerip"]
            outer_ip = host_info.get("bk_host_outerip", "")
            login_ip = host_info.get("login_ip", "")
            # 写入数据库
            if host_info["host_node_type"] == constants.NodeType.PROXY:
                login_ip = login_ip or outer_ip or inner_ip
            else:
                login_ip = login_ip or inner_ip

            extra_data = {
                "peer_exchange_switch_for_agent": host_info.get("peer_exchange_switch_for_agent", True),
                "bt_speed_limit": host_info.get("bt_speed_limit", 0),
            }
            if host_info.get("data_path"):
                extra_data.update({"data_path": host_info.get("data_path")})
            host_obj = models.Host(
                bk_host_id=bk_host_id,
                bk_cloud_id=host_info["bk_cloud_id"],
                bk_biz_id=host_info["bk_biz_id"],
                inner_ip=inner_ip,
                outer_ip=outer_ip,
                login_ip=login_ip,
                data_ip=host_info.get("data_ip", ""),
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

            identity_data_obj = models.IdentityData(
                bk_host_id=bk_host_id,
                auth_type=host_info.get("auth_type"),
                account=host_info.get("account"),
                password=base64.b64decode(host_info.get("password", "")).decode(),
                port=host_info.get("port"),
                key=base64.b64decode(host_info.get("key", "")).decode(),
                retention=host_info.get("retention", 1),
                extra_data=host_info.get("extra_data", {}),
                updated_at=timezone.now(),
            )
            if bk_host_id in host_ids_in_exist_identity_data:
                identity_data_objs_to_be_updated.append(identity_data_obj)
            else:
                identity_data_objs_to_be_created.append(identity_data_obj)

            if bk_host_id not in host_ids_in_exist_proc_statuses:
                proc_status_obj = models.ProcessStatus(
                    bk_host_id=bk_host_id,
                    source_type=ProcessStatus.SourceType.DEFAULT,
                    status=constants.ProcStateType.NOT_INSTALLED,
                    name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                )
                proc_status_objs_to_be_created.append(proc_status_obj)

            sub_inst_obj.instance_info["host"]["bk_host_id"] = bk_host_id
            sub_inst_obj.instance_info["host"]["is_manual"] = host_obj.is_manual
            sub_inst_objs_to_be_updated.append(sub_inst_obj)

        models.Host.objects.bulk_create(host_objs_to_be_created, batch_size=self.batch_size)
        models.Host.objects.bulk_update(
            host_objs_to_be_updated,
            fields=["bk_biz_id", "bk_cloud_id", "inner_ip", "outer_ip", "login_ip", "data_ip", "os_type"]
            + ["is_manual", "ap_id", "install_channel_id", "upstream_nodes", "updated_at", "extra_data"],
            batch_size=self.batch_size,
        )
        models.ProcessStatus.objects.bulk_create(proc_status_objs_to_be_created, batch_size=self.batch_size)
        models.IdentityData.objects.bulk_create(identity_data_objs_to_be_created, batch_size=self.batch_size)
        models.IdentityData.objects.bulk_update(
            identity_data_objs_to_be_updated,
            fields=["auth_type", "account", "password", "port", "key", "retention", "extra_data", "updated_at"],
            batch_size=self.batch_size,
        )
        models.SubscriptionInstanceRecord.objects.bulk_update(
            sub_inst_objs_to_be_updated, fields=["instance_info"], batch_size=self.batch_size
        )

        sub_inst_ids = self.fetch_sub_inst_ids_by_host_keys(
            host_keys=list(host_key__bk_host_id_map.keys()), host_key__sub_inst_map=host_key__sub_inst_map
        )
        self.log_info(sub_inst_ids=sub_inst_ids, log_content=_("注册CMDB完成"))

    def _execute(self, data, parent_data, common_data: AgentCommonData):

        subscription_instances: List[models.SubscriptionInstanceRecord] = common_data.subscription_instances

        # key / password expired, failed
        host_key__sub_inst_map = self.handle_empty_auth_info_case(subscription_instances)

        # host infos group by bk_biz_id and register add_host_to_resource
        host_key__bk_host_id_map = self.handle_add_hosts_to_cmdb_case(host_key__sub_inst_map)

        self.handle_update_db(
            host_key__bk_host_id_map=host_key__bk_host_id_map, host_key__sub_inst_map=host_key__sub_inst_map
        )
