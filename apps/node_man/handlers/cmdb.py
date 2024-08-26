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
import hashlib
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

from blueapps.account.models import User
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import ugettext as _

from apps.component.esbclient import client_v2
from apps.exceptions import ComponentCallError
from apps.iam import Permission
from apps.iam.exceptions import PermissionDeniedError
from apps.iam.handlers.resources import Business
from apps.node_man import constants, models
from apps.node_man.constants import BIZ_CACHE_SUFFIX, DEFAULT_CLOUD_NAME, IamActionType
from apps.node_man.exceptions import (
    CacheExpiredError,
    CloudNotExistError,
    CloudUpdateAgentError,
)
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.periodic_tasks.sync_cmdb_biz_topo_task import (
    cache_all_biz_topo_delay_task,
    get_and_cache_format_biz_topo,
)
from apps.utils import APIModel
from apps.utils.batch_request import batch_request, request_multi_thread
from apps.utils.local import get_request_username
from common.log import logger

# TODO 权限和逻辑层解耦


class CmdbTool:
    @staticmethod
    def get_or_cache_biz_topo(bk_biz_id: int):
        return (
            cache.get(f"{bk_biz_id}_topo_cache")
            or get_and_cache_format_biz_topo(bk_biz_id=bk_biz_id)["biz_format_topo"]
        )


class CmdbHandler(APIModel):
    """
    Cmdb处理器
    """

    @staticmethod
    def cmdb_or_cache_biz(username: str):
        """
        如果有缓存，则返回缓存；
        如果没有缓存，则重新调取接口。
        格式:
        [{
            'bk_biz_id': biz_id ,
            'bk_biz_name': bk_biz_name
        }]
        """
        user_biz_cache = cache.get(username + BIZ_CACHE_SUFFIX)

        if user_biz_cache:
            # 如果存在缓存则返回
            return user_biz_cache
        else:
            # 缓存已过期，重新获取
            kwargs = {"fields": ["bk_biz_id", "bk_biz_name"]}

            # 如果不使用权限中心，则需要拿到业务运维
            if not (settings.USE_IAM or User.objects.filter(username=username, is_superuser=True).exists()):
                kwargs["condition"] = {"bk_biz_maintainer": username}

            try:
                # 需要以用户的名字进行请求
                result = client_v2.cc.search_business(kwargs)
                cache.set(username + BIZ_CACHE_SUFFIX, result, 60)
                return result
            except ComponentCallError as e:
                logger.error("esb->call search_business error %s" % e.message)
                return {"info": []}

    @classmethod
    def biz_id_name_without_permission(cls, username=None) -> Dict[int, str]:

        biz_cache = cache.get("biz_id_name" + BIZ_CACHE_SUFFIX)
        if biz_cache:
            biz_id_name: Dict[int, str] = {}
            for bk_biz_id_str, bk_biz_name in biz_cache.items():
                try:
                    biz_id_name[int(bk_biz_id_str)] = bk_biz_name
                except Exception:
                    logger.warning(f"[biz_id_name_without_permission] bk_biz_id -> {bk_biz_id_str} is not int")
                    biz_id_name[bk_biz_id_str] = bk_biz_name
            return biz_id_name

        username = username or get_request_username()
        all_biz = cls.cmdb_or_cache_biz(username)["info"]
        resource_pool_biz = {"bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID, "bk_biz_name": "资源池"}
        all_biz.insert(0, resource_pool_biz)

        data = {biz["bk_biz_id"]: biz["bk_biz_name"] for biz in all_biz}

        cache.set("biz_id_name" + BIZ_CACHE_SUFFIX, data, 300)

        return data

    def ret_biz_permission(self, param, username=None):
        """
        处理业务权限
        :return: 用户有权限的业务列表
        """

        username = username or get_request_username()
        all_biz = self.cmdb_or_cache_biz(username)["info"]

        # 如果是超管，增加资源池权限
        is_superuser = IamHandler.is_superuser(username)
        if is_superuser:
            resource_pool_biz = {
                "bk_biz_id": settings.BK_CMDB_RESOURCE_POOL_BIZ_ID,
                "bk_biz_name": "资源池",
                "has_permission": True,
            }
            all_biz.insert(0, resource_pool_biz)

        if is_superuser or not settings.USE_IAM:
            for biz in all_biz:
                biz["has_permission"] = True
        else:
            biz_view_permission = IamHandler().fetch_policy(username, [param["action"]])[param["action"]]
            for biz in all_biz:
                biz["has_permission"] = biz["bk_biz_id"] in biz_view_permission
            all_biz = sorted(all_biz, key=lambda x: -x["has_permission"])

        return all_biz

    def cmdb_biz_inst_topo(self, biz):
        """
        搜索业务的拓扑树
        :return:
        """

        kwargs = {"bk_biz_id": biz}
        try:
            # 需要以用户的名字进行请求
            result = client_v2.cc.search_biz_inst_topo(kwargs)
            return result
        except ComponentCallError as e:
            logger.error("esb->call search_biz_inst_topo error %s" % e.message)
            return []

    def cmdb_biz_free_inst_topo(self, biz):
        """
        搜索业务的空闲机池拓扑树
        :return:
        """

        kwargs = {"bk_biz_id": biz}
        try:
            # 需要以用户的名字进行请求
            result = client_v2.cc.get_biz_internal_module(kwargs)
            return result
        except ComponentCallError as e:
            logger.error("esb->call get_biz_internal_module error %s" % e.message)
            return {"info": []}

    @staticmethod
    def cmdb_hosts_by_biz(start, bk_biz_id, bk_set_ids=None, bk_module_ids=None):
        """
        Host列表
        :param start: 开始数
        :param bk_biz_id: 业务ID
        :param bk_set_ids: 集群ID列表
        :param bk_module_ids: 模块ID列表
        :return: 主机列表
        """
        kwargs = {
            "page": {"start": start * 500, "limit": 500, "sort": "bk_host_id"},
            "bk_biz_id": bk_biz_id,
            "fields": ["bk_host_id"],
        }
        try:
            if bk_set_ids:
                kwargs["bk_set_ids"] = bk_set_ids
            if bk_module_ids:
                kwargs["bk_module_ids"] = bk_module_ids
            result = client_v2.cc.list_biz_hosts(kwargs)
            return result
        except ComponentCallError as e:
            logger.error("esb->call list_biz_hosts error %s" % e.message)
            return {"info": []}

    def cmdb_or_cache_topo(self, username: str, user_biz: dict, biz_host_id_map: dict):
        """
        如果有缓存，则返回缓存；
        如果没有缓存，则重新调取接口。
        :param username: 用户名
        :param user_biz:用户业务
        :param biz_host_id_map: 业务和相关Host ID字典
        格式:
        {
            'bk_host_id': ['蓝鲸/集群/模块', ...]
        }
        """

        user_page_topology_cache = cache.get(username + "_" + str(biz_host_id_map) + "_topo_cache")

        if user_page_topology_cache:
            # 如果存在缓存则返回,缓存读出来的key为str，适配后续逻辑转化成整型
            user_page_topology_cache = {int(key): value for key, value in user_page_topology_cache.items()}
            return user_page_topology_cache
        else:
            # 缓存已过期，重新获取
            # 根据业务获得拓扑信息
            topology = {}
            # 异步需要用用户的名字，并且backend为True的形式请求
            with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
                tasks = [
                    ex.submit(CmdbHandler().find_host_topo, username, biz, biz_host_id_map[biz], topology, user_biz)
                    for biz in biz_host_id_map
                ]
                as_completed(tasks)
            cache.set(username + "_" + str(biz_host_id_map) + "_topo_cache", topology, 300)
            return topology

    def biz(self, param, username=None):
        """
        查询用户所有业务
        格式:
        [{
            'bk_biz_id': biz_id ,
            'bk_biz_name': bk_biz_name
        }]
        """

        return self.ret_biz_permission(param, username=username)

    def biz_id_name(self, param, username=None):
        """
        获得用户的业务列表
        :return
        {
            bk_biz_id: bk_biz_name
        }
        """

        result = self.ret_biz_permission(param, username=username)

        return {biz["bk_biz_id"]: biz["bk_biz_name"] for biz in result if biz["has_permission"]}

    def cmdb_update_host(self, bk_host_id, properties):
        """
        更新host的属性
        :param bk_host_id: 需要修改的host的bk_host_id
        :param properties: 需要修改属性值
        :return: 返回查询结果
        """

        kwargs = {"update": [{"properties": properties, "bk_host_id": bk_host_id}]}
        # 增删改查CMDB操作以admin用户进行
        client_v2.cc.batch_update_host(kwargs)

    def cmdb_update_host_cloud(self, kwargs: dict):
        """
        更新host的管控区域属性
        :param kwargs: 参数列表
        :return: None
        """

        # 增删改查CMDB操作以admin用户进行
        client_v2.cc.update_host_cloud_area_field(kwargs)

    def find_host_topo(self, username, bk_biz_id: int, bk_host_ids: list, topology: dict, user_biz: dict):
        kwargs = {
            "bk_biz_id": bk_biz_id,
            "fields": ["bk_host_id"],
            "page": {"start": 0, "limit": len(bk_host_ids)},
            "host_property_filter": {
                "condition": "AND",
                "rules": [{"field": "bk_host_id", "operator": "in", "value": bk_host_ids}],
            },
        }
        # 异步需要用用户的名字，并且backend为True的形式请求
        host_topos = client_v2.cc.list_biz_hosts_topo(kwargs, bk_username=username).get("info") or []
        for topos in host_topos:
            topology[topos["host"]["bk_host_id"]] = []
            # 集群
            for topo in topos["topo"]:
                topo_str = user_biz.get(bk_biz_id) + " / " + topo.get("bk_set_name")
                # 模块
                if topo.get("module", []):
                    for module in topo["module"]:
                        topology[topos["host"]["bk_host_id"]].append(topo_str + " / " + module["bk_module_name"])
        return topology

    def check_biz_permission(self, bk_biz_scope: list, action: str):
        """
        校验业务权限
        :param bk_biz_scope: 业务范围
        :param action: IamActionType
        :return: 校验失败抛异常
        """
        # 校验用户业务权限
        if IamHandler.is_superuser(get_request_username()):
            return True
        user_biz = self.biz_id_name({"action": action})
        diff = set(bk_biz_scope) - set(user_biz.keys())
        if not diff:
            return True
        resources = Business.create_instances(diff)
        apply_data, apply_url = Permission().get_apply_data([action], resources)
        raise PermissionDeniedError(action_name=action, apply_url=apply_url, permission=apply_data)

    @staticmethod
    def add_cloud(bk_cloud_name: str, bk_cloud_vendor: str = None):
        """
        新增管控区域
        """
        # 增删改查CMDB操作以admin用户进行
        data = client_v2.cc.create_cloud_area({"bk_cloud_name": bk_cloud_name, "bk_cloud_vendor": bk_cloud_vendor})
        return data.get("created", {}).get("id")

    @staticmethod
    def delete_cloud(bk_cloud_id):
        """
        删除管控区域
        """
        try:
            # 增删改查CMDB操作以admin用户进行
            return client_v2.cc.delete_cloud_area({"bk_cloud_id": bk_cloud_id})
        except ComponentCallError as e:
            if e.message and e.message["code"] == 1101030:
                raise CloudUpdateAgentError(
                    _("在CMDB中，还有主机关联到当前「管控区域」下，无法删除"),
                )

    @staticmethod
    def get_cloud(bk_cloud_name):
        try:
            # 增删改查CMDB操作以admin用户进行
            plats = client_v2.cc.search_cloud_area({"condition": {"bk_cloud_name": bk_cloud_name}})
        except ComponentCallError as e:
            logger.error("esb->call search_cloud_area error %s" % e.message)
            plats = client_v2.cc.search_inst(
                {
                    "bk_obj_id": "plat",
                    "condition": {"plat": [{"field": "bk_cloud_name", "operator": "$eq", "value": bk_cloud_name}]},
                }
            )

        if plats["info"]:
            return plats["info"][0]["bk_cloud_id"]
        raise CloudNotExistError

    @staticmethod
    def rename_cloud(bk_cloud_id: int, bk_cloud_name: str, bk_cloud_vendor: str = None):
        try:
            # 增删改查CMDB操作以admin用户进行
            client_v2.cc.update_cloud_area(
                {"bk_cloud_id": bk_cloud_id, "bk_cloud_name": bk_cloud_name, "bk_cloud_vendor": bk_cloud_vendor}
            )
        except ComponentCallError as e:
            logger.error("esb->call update_cloud_area error %s" % e.message)
            client_v2.cc.update_inst(
                bk_obj_id="plat", bk_inst_id=bk_cloud_id, bk_cloud_name=bk_cloud_name, bk_cloud_vendor=bk_cloud_vendor
            )

    @classmethod
    def get_or_create_cloud(cls, bk_cloud_name: str, bk_cloud_vendor: str = None):
        try:
            return cls.get_cloud(bk_cloud_name)
        except CloudNotExistError:
            return cls.add_cloud(bk_cloud_name, bk_cloud_vendor=bk_cloud_vendor)

    def fetch_topo(self, bk_biz_id: int, with_biz_node: bool = False) -> List:
        """
        获得相关业务数据的拓扑
        :param bk_biz_id:
        :param with_biz_node: 业务拓扑是否返回业务父节点
        """
        biz_topo = CmdbTool.get_or_cache_biz_topo(bk_biz_id)
        if not with_biz_node:
            return biz_topo.get("children", [])
        return biz_topo

    def fetch_all_topo(self, action=IamActionType.agent_view) -> List:
        user_biz = self.biz_id_name({"action": action})
        topo_list = []
        with ThreadPoolExecutor(max_workers=settings.CONCURRENT_NUMBER) as ex:
            tasks = [ex.submit(self.fetch_topo, biz_id, True) for biz_id in user_biz]
            for future in as_completed(tasks):
                topo_list.append(future.result())
        return topo_list

    @classmethod
    def search_topo_nodes(cls, params, action=IamActionType.agent_view):
        """
        查询拓扑节点
        :param params: 查询参数 [`kw`, `bk_biz_ids`, `page`, `pagesize`]
        :param action:
        :return:
        {
            "total": 3,
            "nodes": [
                {"name": "pbiz", "id": 12, "type": "biz", "path": "pbiz"},
                {"name": "p2", "id": 123, "type": "set", "path": "pbiz / p2"},
                {"name": "p4", "id": 1324, "type": "set", "path": "pbiz / p4"},
            ],
            "use_cache": True
        }
        """
        is_page = False
        begin, end = None, None
        if "page" in params and "pagesize" in params:
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
            is_page = True

        if params.get("action"):
            action = params["action"]

        # 筛出用户有权限的业务ID列表
        user_biz_ids = CmdbHandler().biz_id_name({"action": action})

        if "bk_biz_ids" in params:
            # 指定搜索ID列表，取交集搜索，保证搜索业务均在用户权限内
            target_biz_ids = list(set(params["bk_biz_ids"]) & set(user_biz_ids))
        else:
            target_biz_ids = user_biz_ids

        hl = hashlib.md5()
        hl.update("|".join([str(biz_id) for biz_id in sorted(target_biz_ids)]).encode(encoding="utf-8"))
        biz_ids_md5 = hl.hexdigest()

        # 生成长度降序关键字前缀
        possible_keys = [
            "{biz_ids_md5}_{kw}_topo_search_res".format(biz_ids_md5=biz_ids_md5, kw=params["kw"][idx:])
            for idx in range(0, len(params["kw"]))
        ]

        possible_cache = cache.get_many(possible_keys)
        # 获取在缓存中关键字的最长前缀
        hit_longest_prefix = next((key for key in possible_keys if key in possible_cache), None)

        possible_nodes = []
        use_cache = False
        if hit_longest_prefix is None:
            # 关键字搜索缓存不命中，全局搜索
            biz_group_nodes = cache.get_many([f"{bk_biz_id}_topo_nodes" for bk_biz_id in target_biz_ids])

            # 最坏情况：业务节点缓存过期，此时开启延时任务更新缓存
            if not biz_group_nodes and len(target_biz_ids) != 0:
                cache_all_biz_topo_delay_task.delay()
                logger.warning(
                    "API[/cmdb/biz/search_topo/]: bk_biz_ids -> {bk_biz_ids} nodes cache expired".format(
                        bk_biz_ids=target_biz_ids
                    )
                )
                raise CacheExpiredError()
            for biz_id in biz_group_nodes:
                possible_nodes = possible_nodes + biz_group_nodes[biz_id]
        else:
            # kw的搜索结果在最长前缀的基础上迭代
            use_cache = True
            possible_nodes = possible_cache[hit_longest_prefix]
            # 最长前缀是关键字本身，返回搜索结果
            if possible_keys[0] == hit_longest_prefix:
                return {
                    "total": len(possible_nodes),
                    "nodes": possible_nodes[begin:end] if is_page else possible_nodes,
                    "use_cache": use_cache,
                }

        match_nodes = [node for node in possible_nodes if params["kw"] in node["name"]]

        # 使用缓存情况下，如果上一次搜索结果不是空才需要设置缓存，防止缓存key-value被挤爆
        if not use_cache or (use_cache and len(possible_nodes) != 0):
            cache.set(possible_keys[0], match_nodes, 60)
        return {
            "total": len(match_nodes),
            "nodes": match_nodes[begin:end] if is_page else match_nodes,
            "use_cache": use_cache,
        }

    @classmethod
    def search_ip(cls, params):
        """
        查询拓扑节点
        :param params: 查询参数 [`kw`, `bk_biz_ids`, `page`, `pagesize`]
        :return:
        {
            "total": 2,
            "nodes": [
            {
                "bk_biz_id": 14,
                "bk_host_id": 221442,
                "bk_cloud_id": 0,
                "inner_ip": "1.1.1.1",
                "os_type": "LINUX",
                "bk_cloud_name": "直连区域",
                "status": "UNREGISTER"
            },
            {
                "bk_biz_id": 14,
                "bk_host_id": 221430,
                "bk_cloud_id": 0,
                "inner_ip": "2.2.2.2",
                "os_type": "LINUX",
                "bk_cloud_name": "直连区域",
                "status": "UNREGISTER"
            }
            ],
        }
        """
        is_page = False
        begin, end = None, None
        if "page" in params and "pagesize" in params:
            begin = (params["page"] - 1) * params["pagesize"]
            end = (params["page"]) * params["pagesize"]
            is_page = True

        # 筛出用户有权限的业务ID列表
        user_biz_ids = CmdbHandler().biz_id_name({"action": IamActionType.agent_view})

        if "bk_biz_ids" in params:
            # 指定搜索ID列表，取交集搜索，保证搜索业务均在用户权限内
            target_biz_ids = list(set(params["bk_biz_ids"]) & set(user_biz_ids))
        else:
            target_biz_ids = user_biz_ids

        cloud_info = models.Cloud.objects.all().values("bk_cloud_id", "bk_cloud_name")
        cloud_info_map = {info["bk_cloud_id"]: info["bk_cloud_name"] for info in cloud_info}
        cloud_info_map[0] = str(DEFAULT_CLOUD_NAME)

        query_host = models.Host.objects.filter(inner_ip__contains=params["kw"], bk_biz_id__in=target_biz_ids)

        match_agent_status = models.ProcessStatus.objects.filter(
            bk_host_id__in=query_host.values_list("bk_host_id", flat=True)
        ).values("bk_host_id", "status")
        match_agent_status_map = {info["bk_host_id"]: info["status"] for info in match_agent_status}

        match_host = query_host.values("bk_biz_id", "bk_host_id", "bk_cloud_id", "inner_ip", "os_type")
        paged_hosts = match_host[begin:end] if is_page else match_host
        for host in paged_hosts:
            host["bk_cloud_name"] = cloud_info_map[host["bk_cloud_id"]]
            host["status"] = match_agent_status_map[host["bk_host_id"]]

        return {
            "total": match_host.count(),
            "nodes": list(paged_hosts),
        }

    @staticmethod
    def get_topo_order():
        """
        获取主线模型的业务拓扑层级顺序
        :return: ["biz", "set", "module", "host"]
        """
        topo = client_v2.cc.get_mainline_object_topo()
        return [obj["bk_obj_id"] for obj in topo]

    @staticmethod
    def find_host_service_template(bk_host_ids: List[int]) -> List[Dict]:
        """
        查询主机服务模板
        :return: [{"bk_host_id": 1, "service_template_id": [2, 3]}]
        """
        # CMDB 限制了单次查询数量，这里需分批并发请求查询
        param_list = [
            {
                "bk_host_id": bk_host_ids[
                    page
                    * constants.QUERY_HOST_SERVICE_TEMPLATE_LIMIT : (page + 1)
                    * constants.QUERY_HOST_SERVICE_TEMPLATE_LIMIT
                ]
            }
            for page in range(math.ceil(len(bk_host_ids) / constants.QUERY_HOST_SERVICE_TEMPLATE_LIMIT))
        ]
        host_service_templates = request_multi_thread(
            client_v2.cc.find_host_service_template, param_list, get_data=lambda x: x
        )
        return host_service_templates

    @staticmethod
    def get_biz_service_template(bk_biz_id: int) -> List[Dict]:
        return batch_request(client_v2.cc.list_service_template, {"bk_biz_id": bk_biz_id})
