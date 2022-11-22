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
from collections import Counter, defaultdict

from django.db.models import CharField, Q, QuerySet, Value
from django.db.models.functions import Concat

from apps.node_man import constants as node_man_constants
from apps.node_man import models as node_man_models
from apps.utils import basic, concurrent

from .. import constants, types
from ..query import resource


class HostQuerySqlHelper:
    @staticmethod
    def fetch_cloud_ids_by_name(name: str) -> typing.List[int]:
        return list(
            node_man_models.Cloud.objects.filter(bk_cloud_name__icontains=name).values_list("bk_cloud_id", flat=True)
        )

    @classmethod
    def fuzzy_cond(
        cls,
        cond_val: str,
        wheres: typing.List[str],
        sql_params: typing.List[str],
        fuzzy_search_fields: typing.List[str],
    ) -> typing.Tuple[typing.List[str], typing.List[str]]:
        """
        用于生成模糊搜索的条件
        :param cond_val: 用户的输入
        :param wheres: Where 语句列表
        :param sql_params: escape 参数列表
        :param fuzzy_search_fields:
        :return: where, sql_params
        """

        where_or: typing.List[str] = []

        for fuzzy_search_field in fuzzy_search_fields:
            if fuzzy_search_field == "bk_cloud_id":
                # 云区域的模糊搜索是通过云区域名称进行的，需要通过名称先模糊匹配
                cloud_ids_str: str = ",".join(
                    [str(cloud_id) for cloud_id in cls.fetch_cloud_ids_by_name(name=cond_val)]
                )
                if cloud_ids_str:
                    where_or.append(f"{node_man_models.Host._meta.db_table}.{fuzzy_search_field} in (%s)")
                    sql_params.append(cloud_ids_str)
            else:
                where_or.append(f"{node_man_models.Host._meta.db_table}.{fuzzy_search_field} like %s")
                sql_params.extend([f"%{cond_val}%"])

        wheres.append(f"( {' OR '.join(where_or)} )")

        return wheres, sql_params

    @staticmethod
    def handle_plugin_conditions(
        params: typing.Dict, plugin_names: typing.List[str], return_sql: bool = True
    ) -> typing.Union[typing.List[int], str]:
        print("params", params)
        if not params.get("conditions"):
            return []

        select: typing.Dict[str, str] = {
            "status": f"{node_man_models.ProcessStatus._meta.db_table}.status",
            "version": f"{node_man_models.ProcessStatus._meta.db_table}.version",
        }
        wheres: typing.List[str] = []
        init_wheres = [
            f"{node_man_models.Host._meta.db_table}.bk_host_id="
            f"{node_man_models.ProcessStatus._meta.db_table}.bk_host_id",
            f'{node_man_models.ProcessStatus._meta.db_table}.proc_type="{node_man_constants.ProcType.PLUGIN}"',
            f"{node_man_models.ProcessStatus._meta.db_table}.source_type="
            f'"{node_man_models.ProcessStatus.SourceType.DEFAULT}"',
            f"{node_man_models.ProcessStatus._meta.db_table}.is_latest=true",
        ]
        for condition in params["conditions"]:

            if condition["key"] in ["source_id", "plugin_name"]:
                key: str = {"source_id": "source_id", "plugin_name": "name"}[condition["key"]]
                placeholder = [f'"{cond_val}"' for cond_val in condition["value"]]
                wheres.append(f'{node_man_models.ProcessStatus._meta.db_table}.{key} in ({",".join(placeholder)})')

            if condition["key"] in plugin_names:
                # 插件版本的精确搜索
                placeholder = []
                for cond_val in condition["value"]:
                    if cond_val == -1:
                        # 无版本插件筛选
                        placeholder.append('""')
                    else:
                        placeholder.append('"{}"'.format(cond_val))
                wheres.append(f'{node_man_models.ProcessStatus._meta.db_table}.version in ({",".join(placeholder)})')
                wheres.append(f'{node_man_models.ProcessStatus._meta.db_table}.name="{condition["key"]}"')

            elif condition["key"] in [f"{plugin}_status" for plugin in plugin_names]:
                # 插件状态的精确搜索
                placeholder = []
                for cond_val in condition["value"]:
                    placeholder.append('"{}"'.format(cond_val))
                plugin_name: str = "_".join(condition["key"].split("_")[:-1])
                wheres.append(f'{node_man_models.ProcessStatus._meta.db_table}.status in ({",".join(placeholder)})')
                wheres.append(f'{node_man_models.ProcessStatus._meta.db_table}.name="{plugin_name}"')

        if wheres:
            wheres = init_wheres + wheres
            host_queryset: QuerySet = (
                node_man_models.Host.objects.extra(
                    select=select, tables=[node_man_models.ProcessStatus._meta.db_table], where=wheres
                )
                .order_by()
                .values_list("bk_host_id", flat=True)
            )
            if return_sql:
                return host_queryset.query
            else:
                return set(host_queryset) or [-1]
        return []

    @staticmethod
    def fetch_match_node_types(is_proxy: bool, return_all_node_type: bool) -> typing.List[str]:
        if is_proxy:
            # 单独查代理
            return [node_man_constants.NodeType.PROXY]
        elif return_all_node_type:
            # 查插件，或者返回全部类型的情况
            return [
                node_man_constants.NodeType.AGENT,
                node_man_constants.NodeType.PAGENT,
                node_man_constants.NodeType.PROXY,
            ]
        else:
            # 查 Agent
            return [node_man_constants.NodeType.AGENT, node_man_constants.NodeType.PAGENT]

    @classmethod
    def multiple_cond_sql(
        cls,
        params: typing.Dict,
        biz_scope: typing.Iterable[int],
        is_proxy: bool = False,
        return_all_node_type: bool = False,
        extra_wheres: typing.List[str] = None,
    ) -> QuerySet:
        """
        用于生成多条件sql查询
        :param return_all_node_type: 是否返回所有类型
        :param params: 条件数据
        :param biz_scope: 业务范围限制
        :param is_proxy: 是否为代理
        :param extra_wheres: 额外的查询条件
        :return: 根据条件查询的所有结果
        """
        select: typing.Dict[str, str] = {
            "status": f"{node_man_models.ProcessStatus._meta.db_table}.status",
            "version": f"{node_man_models.ProcessStatus._meta.db_table}.version",
        }

        # 查询参数设置，默认为Host接口搜索
        # 如果需要搜索插件版本，wheres[1]的proc_type将变动为PLUGIN
        sql_params: typing.List[str] = []
        init_wheres: typing.List[str] = [
            f"{node_man_models.Host._meta.db_table}.bk_host_id="
            f"{node_man_models.ProcessStatus._meta.db_table}.bk_host_id",
            f'{node_man_models.ProcessStatus._meta.db_table}.proc_type="{node_man_constants.ProcType.AGENT}"',
            f"{node_man_models.ProcessStatus._meta.db_table}.source_type="
            f'"{node_man_models.ProcessStatus.SourceType.DEFAULT}"',
        ]
        wheres: typing.List[str] = extra_wheres or []

        final_biz_scope: typing.Set[int] = set(biz_scope)
        # 带有业务筛选条件，需要确保落在指定业务范围内
        if params.get("bk_biz_id"):
            final_biz_scope = final_biz_scope & set(params["bk_biz_id"])

        filter_q: Q = Q(bk_biz_id__in=final_biz_scope)
        if params.get("bk_host_id") is not None:
            filter_q &= Q(bk_host_id__in=params.get("bk_host_id"))

        # 条件搜索
        where_or = []
        topo_host_ids: typing.Optional[typing.Set[int]] = None
        topo_biz_scope: typing.Set[int] = set()

        for condition in params.get("conditions", []):
            if condition["key"] in [
                "inner_ip",
                "inner_ipv6" "node_from",
                "node_type",
                "bk_addressing",
                "bk_host_name",
                "bk_agent_id",
            ]:
                if condition["key"] in ["inner_ipv6"]:
                    condition["value"] = basic.ipv6s_formatter(condition["value"])
                # host 精确搜索
                filter_q &= Q(**{f"{condition['key']}__in": condition["value"]})

            elif condition["key"] in ["ip"]:
                ipv6s: typing.Set[str] = set()
                ipv4s: typing.Set[str] = set()

                for ip in condition["value"]:
                    if basic.is_v6(ip):
                        ipv6s.add(basic.exploded_ip(ip))
                    else:
                        ipv4s.add(ip)

                filter_q &= Q(inner_ip__in=ipv4s) | Q(inner_ipv6__in=ipv6s)

            elif condition["key"] in ["os_type"]:
                # 如果传的是 none，替换成 ""
                filter_q &= Q(
                    **{f"{condition['key']}__in": list(map(lambda x: (x, "")[x == "none"], condition["value"]))}
                )

            elif condition["key"] in ["status", "version"]:
                # process_status 精确搜索
                placeholder: typing.List[str] = []
                for cond_val in condition["value"]:
                    placeholder.append("%s")
                    sql_params.append(cond_val)
                wheres.append(
                    f'{node_man_models.ProcessStatus._meta.db_table}.{condition["key"]} in ({",".join(placeholder)})'
                )

            elif condition["key"] in ["is_manual", "bk_cloud_id", "install_channel_id"]:
                # 对于数字类过滤条件，保证过滤值全数字再拼生成 SQL，否则该条件置空
                is_digit_list: bool = "".join([str(cond_val) for cond_val in condition["value"]]).isdigit()
                if is_digit_list:
                    filter_q &= Q(**{f"{condition['key']}__in": condition["value"]})

            elif condition["key"] == "topology":
                # 集群与模块的精准搜索
                topo_biz_id: int = condition["value"].get("bk_biz_id")
                if topo_biz_id not in final_biz_scope:
                    # 对于单个拓扑查询条件，没有落在业务范围内时 bk_host_id__in 不叠加即可
                    # 无需清空列表，否则之前累积落在业务范围内的主机 ID 查询条件也会跟着被清空
                    continue
                bk_set_ids: typing.List[int] = condition["value"].get("bk_set_ids") or []
                bk_module_ids: typing.List[int] = condition["value"].get("bk_module_ids") or []
                # 传入拓扑是一个业务节点，无需计算主机 ID 列表，直接从数据库获取 bk_host_id
                if len(bk_set_ids) == 0 and len(bk_module_ids) == 0:
                    topo_biz_scope.add(topo_biz_id)
                    continue

                if bk_module_ids:
                    extra_kwargs = {
                        "filter_obj_id": constants.ObjectType.MODULE.value,
                        "filter_inst_ids": list(set(bk_module_ids)),
                    }
                else:
                    extra_kwargs = {
                        "filter_obj_id": constants.ObjectType.SET.value,
                        "filter_inst_ids": list(set(bk_set_ids)),
                    }

                host_infos: typing.List[types.HostInfo] = resource.ResourceQueryHelper.fetch_biz_hosts(
                    bk_biz_id=topo_biz_id, fields=["bk_host_id"], **extra_kwargs
                )
                host_ids: typing.Set[int] = {host_info["bk_host_id"] for host_info in host_infos}

                if topo_host_ids is None:
                    topo_host_ids = host_ids
                else:
                    topo_host_ids = topo_host_ids | host_ids

            elif condition["key"] == "query" and isinstance(condition["value"], str):
                fuzzy_search_fields: typing.List[str] = (
                    condition.get("fuzzy_search_fields") or constants.CommonEnum.DEFAULT_HOST_FUZZY_SEARCH_FIELDS.value
                )
                wheres, sql_params = cls.fuzzy_cond(
                    cond_val=condition["value"],
                    wheres=wheres,
                    sql_params=sql_params,
                    fuzzy_search_fields=fuzzy_search_fields,
                )

            elif condition["key"] == "query" and isinstance(condition["value"], list):
                fuzzy_search_fields: typing.List[str] = (
                    condition.get("fuzzy_search_fields") or constants.CommonEnum.DEFAULT_HOST_FUZZY_SEARCH_FIELDS.value
                )
                for cond_val in condition["value"]:
                    where_or, sql_params = cls.fuzzy_cond(
                        cond_val=cond_val,
                        wheres=where_or,
                        sql_params=sql_params,
                        fuzzy_search_fields=fuzzy_search_fields,
                    )

        wheres = init_wheres + wheres
        if where_or:
            # 用AND连接
            wheres = [" AND ".join(wheres) + " AND (" + " OR ".join(where_or) + ")"]

        # 拓扑搜索按逻辑或进行检索
        topo_query = Q()
        if topo_biz_scope:
            topo_query = topo_query | Q(bk_biz_id__in=topo_biz_scope)
        if topo_host_ids is not None:
            topo_query = topo_query | Q(bk_host_id__in=topo_host_ids)

        host_queryset: QuerySet = (
            node_man_models.Host.objects.filter(
                node_type__in=cls.fetch_match_node_types(is_proxy, return_all_node_type), bk_biz_id__in=final_biz_scope
            )
            .extra(
                select=select, tables=[node_man_models.ProcessStatus._meta.db_table], where=wheres, params=sql_params
            )
            .filter(filter_q)
            .filter(topo_query)
        )

        return host_queryset

    @classmethod
    def paginate_queryset(cls, queryset: QuerySet, start: int, page_size: int) -> QuerySet:
        """
        返回分页后的 queryset
        :param queryset:
        :param start:
        :param page_size:
        :return:
        """
        if page_size == constants.CommonEnum.PAGE_RETURN_ALL_FLAG.value:
            # 全选，置空在后续切片时即选择全量
            start: typing.Optional[int] = None
            end: typing.Optional[int] = None
        else:
            # 正常分片
            start: typing.Optional[int] = start
            end: typing.Optional[int] = start + page_size
        return queryset[start:end]


class HostQueryHelper:
    @classmethod
    def fetch_set_ids(cls, bk_biz_id: int, target_inst_ids: typing.Iterable[int]) -> typing.List[int]:
        """
        获取指定节点实例 ID 列表下的集群 ID 列表
        :param bk_biz_id: 业务 ID
        :param target_inst_ids: 节点实例 ID 列表
        :return:
        """
        target_inst_ids: typing.Set[int] = set(target_inst_ids)
        topo_tree: types.TreeNode = resource.ResourceQueryHelper.get_topo_tree(bk_biz_id)

        # 遍历拓扑，将指定实例 ID 节点（子树）加入 child_topo_tree_stack
        child_topo_tree_stack: typing.List[types.TreeNode] = []
        topo_tree_stack: typing.List[types.TreeNode] = [topo_tree]
        while topo_tree_stack:
            node: types.TreeNode = topo_tree_stack.pop()
            if node["bk_inst_id"] in target_inst_ids:
                child_topo_tree_stack.append(node)
                if len(child_topo_tree_stack) == len(target_inst_ids):
                    # 已完成查询，提前返回减少无效遍历
                    break
                continue
            topo_tree_stack.extend(node.get("child", []))

        # 遍历获取的子树，从中获取集群 ID
        set_ids: typing.Set[int] = set()
        while child_topo_tree_stack:
            node: types.TreeNode = child_topo_tree_stack.pop()
            if node["bk_inst_id"] == constants.ObjectType.SET.value:
                set_ids.add(node["bk_inst_id"])
                continue
            child_topo_tree_stack.extend(node.get("child", []))

        return list(set_ids)

    @classmethod
    def parse_nodes2conditions(
        cls, node_list: typing.List[types.TreeNode]
    ) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        根据拓扑节点列表生成主机查询条件
        :param node_list: 拓扑节点列表
        :return:
        """
        # 查询条件仅支持 set / module ids 单传，需要按 obj id 聚合，生成多条 condition
        nodes_gby_biz_and_obj_id: typing.Dict[str, typing.List[types.TreeNode]] = defaultdict(list)
        for node in node_list:
            nodes_gby_biz_and_obj_id[f"{node['bk_biz_id']}-{node['bk_obj_id']}"].append(node)

        params_list: typing.List[typing.Dict] = []
        conditions: typing.List[typing.Dict[str, typing.Any]] = []
        for partial_node_list in nodes_gby_biz_and_obj_id.values():
            # 已按 bk_obj_id 聚合，所以取其中一个判断对象类型即可
            first_node: types.TreeNode = partial_node_list[0]
            bk_inst_ids: typing.List[int] = list({node["bk_inst_id"] for node in partial_node_list})
            if first_node["bk_obj_id"] in constants.ObjectType.list_member_values():
                # 非自定义层级，直接构造过滤条件
                conditions.append(
                    {
                        "key": "topology",
                        "value": {
                            "bk_biz_id": first_node["bk_biz_id"],
                            f"bk_{first_node['bk_obj_id']}_ids": bk_inst_ids,
                        },
                    }
                )
            else:
                # 自定义层级需要先获取集群 ID，暂存参数，后续并发获取，提高效率
                params_list.append({"_bk_biz_id": first_node["bk_biz_id"], "_target_inst_ids": bk_inst_ids})

        def _get_custom_objs_cond(
            _bk_biz_id: int, _target_inst_ids: typing.List[int]
        ) -> typing.Dict[str, typing.Union[int, typing.List[int]]]:
            """对 fetch_set_ids 做一层封装，构造 cond 结构"""
            return {"bk_biz_id": _bk_biz_id, "bk_set_ids": cls.fetch_set_ids(_bk_biz_id, _target_inst_ids)}

        # 并发构造查询条件
        conditions.extend(concurrent.batch_call(func=_get_custom_objs_cond, params_list=params_list))

        return conditions

    @classmethod
    def query_hosts_base(
        cls,
        node_list: typing.List[types.TreeNode],
        conditions: typing.List[types.Condition],
        limit_host_ids: typing.Optional[typing.List[int]] = None,
    ) -> QuerySet:
        """
        查询主机基础方法
        :param node_list: 拓扑节点
        :param conditions: 查询条件
        :param limit_host_ids: 限制检索的主机 ID 列表
        :return:
        """
        biz_scope: typing.Set[int] = set()
        for node in node_list:
            biz_scope.add(node["bk_biz_id"])
        # 将节点转为查询条件
        conditions.extend(cls.parse_nodes2conditions(node_list))
        # 查询主机
        host_queryset: QuerySet = HostQuerySqlHelper.multiple_cond_sql(
            params={"conditions": conditions}, biz_scope=biz_scope, return_all_node_type=True
        )
        if limit_host_ids is not None:
            host_queryset = host_queryset.filter(bk_host_id__in=limit_host_ids)
        return host_queryset

    @classmethod
    def or_query_hosts(cls, host_queryset: QuerySet, or_conditions: typing.List[types.Condition]) -> QuerySet:
        """
        逻辑或查询主机
        :param host_queryset: 经过 multiple_cond_sql 产生 queryset
        :param or_conditions: 逻辑或查询条件
        :return:
        """
        or_query = Q()
        for or_condition in or_conditions:
            if or_condition["key"] in ["inner_ip", "inner_ipv6", "bk_host_name", "bk_host_id"]:
                if or_condition["key"] in ["inner_ipv6"]:
                    or_condition["val"] = basic.ipv6s_formatter(or_condition["val"])
                or_query = or_query | Q(**{f"{or_condition['key']}__in": or_condition["val"]})
            elif or_condition["key"] in ["cloud_inner_ip", "cloud_inner_ipv6"]:
                __, key = or_condition["key"].split("_", 1)
                # 多字段拼接
                host_queryset = host_queryset.annotate(
                    **{or_condition["key"]: Concat("bk_cloud_id", Value(":"), key, output_field=CharField())}
                )
                or_query = or_query | Q(**{f"{or_condition['key']}__in": or_condition["val"]})

        return host_queryset.filter(or_query)

    @staticmethod
    def get_agent_statistics(host_queryset: QuerySet) -> typing.Dict:
        """
        获取 Agent 状态统计
        :param host_queryset: 经过 multiple_cond_sql 产生 queryset
        :return: Agent 状态统计信息
        """
        # 按 status group by
        statuses: typing.List[str] = list(host_queryset.values_list("status", flat=True))

        total: int = len(statuses)
        status__count_map: typing.Dict[str, int] = dict(Counter(statuses))

        # 转为可读格式
        running_count: int = status__count_map.get(node_man_constants.ProcStateType.RUNNING, 0)
        not_install_count: int = status__count_map.get(node_man_constants.ProcStateType.NOT_INSTALLED, 0)
        return {
            "total": total,
            node_man_constants.ProcStateType.RUNNING: running_count,
            node_man_constants.ProcStateType.NOT_INSTALLED: not_install_count,
            # 将 RUNNING / NOT_INSTALLED 外的状态汇总为 TERMINATED
            node_man_constants.ProcStateType.TERMINATED: total - running_count - not_install_count,
        }
