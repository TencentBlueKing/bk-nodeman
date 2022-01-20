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
import itertools
import operator
from collections import Counter
from functools import reduce
from typing import Any, Dict, List, Union

from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from apps.node_man import constants, models


class JobTools:
    @classmethod
    def get_current_step_display(cls, instance_status: Dict[str, Any]) -> Dict[str, Union[str, int]]:
        """
        用于判断当前状态
        :param instance_status: pipeline 返回结果
        :return: node_id: 当前步骤ID 7为已完成, display: 当前步骤中文名
        """
        try:
            sub_steps = instance_status["steps"][0]["target_hosts"][0]["sub_steps"]
        except (IndexError, KeyError):
            return {"node_id": -1, "status_display": _("节点异常"), "step": ""}

        for step in sub_steps:
            if step["status"] == constants.JobStatusType.RUNNING:
                return {
                    "node_id": step.get("index"),
                    "status_display": _("正在 {node_name}").format(node_name=step["node_name"]),
                    "step": step["node_name"],
                }
            elif step["status"] == constants.JobStatusType.FAILED:
                return {
                    "node_id": step.get("index"),
                    "status_display": _("{node_name} 失败").format(node_name=step["node_name"]),
                    "step": step["node_name"],
                }

        last_step = sub_steps[-1]
        if last_step["status"] == constants.JobStatusType.SUCCESS:
            return {"node_id": last_step.get("index"), "status_display": _("执行成功"), "step": last_step["node_name"]}
        else:
            return {"node_id": -1, "status_display": _("等待执行"), "step": last_step["node_name"]}

    @classmethod
    def get_job_type_in_inst_status(cls, instance_status: Dict[str, Any], default: str) -> str:
        """
        获取
        :param instance_status:
        :param default:
        :return:
        """
        try:
            return constants.ACTION_NAME_JOB_TYPE_MAP[instance_status["steps"][0]["action"]]
        except (IndexError, KeyError):
            return default

    @classmethod
    def parse_job_list_filter_kwargs(cls, query_params: Dict[str, Any]) -> Dict[str, Any]:
        filter_kwargs = {
            "job_type__in": cls.parse2job_types(
                step_types=query_params.get("step_type"), op_types=query_params.get("op_type")
            )
        }

        if query_params.get("policy_name"):
            sub_ids = list(
                models.Subscription.objects.filter(name__in=set(query_params["policy_name"])).values_list(
                    "id", flat=True
                )
            )
            filter_kwargs["subscription_id__in"] = sub_ids

        return filter_kwargs

    @classmethod
    def parse2job_types(cls, step_types: Union[List[str], None], op_types: Union[List[str], None]) -> List[str]:
        # 按选中步骤类型过滤任务类型
        step_types = step_types or [step_type_upper.lower() for step_type_upper in constants.SUB_STEP_TUPLE]
        all_job_types = list(
            itertools.chain(*[constants.JOB_TYPE_MAP.get(step_type.lower(), []) for step_type in step_types])
        )

        job_types_selected = []
        op_types = op_types or list(constants.OP_TYPE_TUPLE)
        for job_type in all_job_types:
            # 按选中的操作类型过滤任务类型
            if [op_type for op_type in op_types if op_type == cls.unzip_job_type(job_type)["op_type"]]:
                job_types_selected.append(job_type)

        return job_types_selected

    @classmethod
    def unzip_job_type(cls, job_type: str):
        op_type_untreated, step_type = job_type.rsplit("_", 1)
        op_type = op_type_untreated.replace("MAIN_", "")
        return {
            # TODO: 保留type用于兼容retrieve接口的meta信息，后续统一为step_type
            "type": step_type,
            "step_type": step_type,
            "op_type": op_type,
            "op_type_display": constants.OP_TYPE_ALIAS_MAP.get(op_type, op_type),
            "step_type_display": constants.SUB_STEP_ALIAS_MAP.get(step_type, step_type),
        }

    @classmethod
    def update_job_statistics(cls, job: models.Job, status_counter: Dict[str, int]):
        """
        更新任务执行状态
        :param job:
        :param status_counter:
        :return:
        """

        # 补充error_hosts的状态
        extra_statuses = []
        for error_host in job.error_hosts:
            # 优先使用已指定的状态，无指定状态默认为忽略（IGNORED）
            # 采用 or 替代 get default，兼容status key存在且为空值的情况
            error_host["status"] = error_host.get("status") or constants.JobStatusType.IGNORED
            extra_statuses.append(error_host["status"])

        status_counter_list = [status_counter, dict(Counter(extra_statuses))]

        # 需要统计的状态
        statuses = [
            constants.JobStatusType.PENDING,
            constants.JobStatusType.RUNNING,
            constants.JobStatusType.SUCCESS,
            constants.JobStatusType.FAILED,
            constants.JobStatusType.IGNORED,
        ]
        statistics = {}
        for status in statuses:
            statistics[f"{status.lower()}_count"] = sum([counter.get(status, 0) for counter in status_counter_list])
        statistics["total_count"] = sum(statistics.values())

        if statistics["total_count"] == 0:
            # 总数为零，认为是任务准备阶段
            job.status = constants.JobStatusType.PENDING
        elif statistics["ignored_count"] == statistics["total_count"]:
            # 主机全部被忽略，此时任务算执行成功
            job.status = constants.JobStatusType.SUCCESS
        elif statistics["running_count"] + statistics["pending_count"] == 0:
            # 没有正在执行的主机，此时需要确定任务成功or失败
            if statistics["failed_count"] == 0:
                job.status = constants.JobStatusType.SUCCESS
            elif statistics["success_count"] == 0:
                job.status = constants.JobStatusType.FAILED
            else:
                job.status = constants.JobStatusType.PART_FAILED
        elif statistics["running_count"]:
            job.status = constants.JobStatusType.RUNNING

        # 任务已完成，需要更新end_time
        if not job.end_time and job.status not in [constants.JobStatusType.PENDING, constants.JobStatusType.RUNNING]:
            job.end_time = timezone.now()
        # 缓存一份统计数据到Job
        job.statistics.update(statistics)
        job.save(update_fields=["status", "end_time", "statistics"])

    @classmethod
    def parse2task_result_query_params(cls, job: models.Job, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        将retrieve请求参数转化为backend task_result的请求参数
        :param job:
        :param query_params:
        :return:
        """
        filter_key_value_list_map = {"instance_id": [], "ip": [], "status": []}
        conditions = query_params.get("conditions")
        if conditions is not None:
            for condition in conditions:
                # 过滤ip
                if condition["key"] in ["ip", "instance_id"]:
                    if isinstance(condition["value"], str):
                        filter_key_value_list_map[condition["key"]].append(condition["value"])
                    elif isinstance(condition["value"], list):
                        filter_key_value_list_map[condition["key"]].extend(condition["value"])
                # 过滤状态字段
                elif condition["key"] == "status":
                    filter_key_value_list_map[condition["key"]].extend(condition["value"])

        host_query = Q()
        fuzzy_inner_ips = filter_key_value_list_map["ip"]
        if fuzzy_inner_ips:
            host_query &= reduce(operator.or_, (Q(inner_ip__contains=fuzzy_ip) for fuzzy_ip in fuzzy_inner_ips))
        instance_ids = filter_key_value_list_map["instance_id"]
        base_fields = {
            "node_type": models.Subscription.NodeType.INSTANCE,
            "object_type": models.Subscription.ObjectType.HOST,
        }
        if host_query:
            from apps.backend.subscription.tools import create_node_id

            for host in list(models.Host.objects.filter(host_query).values("inner_ip", "bk_cloud_id", "bk_host_id")):
                instance_ids.extend(
                    [
                        create_node_id(
                            {
                                **base_fields,
                                "ip": host["inner_ip"],
                                "bk_cloud_id": host["bk_cloud_id"],
                                "bk_supplier_id": constants.DEFAULT_CLOUD,
                            }
                        ),
                        create_node_id({**base_fields, "bk_host_id": host["bk_host_id"]}),
                    ]
                )
        else:
            # None表示缺省全选
            instance_ids = instance_ids or None

        task_result_query_params = {
            "page": query_params["page"],
            "pagesize": query_params["pagesize"],
            "instance_id_list": instance_ids,
            "statuses": filter_key_value_list_map["status"] or None,
            "subscription_id": job.subscription_id,
            "task_id_list": job.task_id_list,
            "return_all": query_params["pagesize"] == -1,
        }
        # None视为全选，空列表视为查询条件
        for query_kw in ["statuses", "instance_id_list"]:
            if task_result_query_params[query_kw] is not None:
                continue
            task_result_query_params.pop(query_kw)

        return task_result_query_params

    @classmethod
    def fill_sub_info_to_job_detail(cls, job: models.Job, job_detail: Dict[str, Any]) -> None:
        """
        填充订阅相关信息到任务详细，通过对象引用特性进行填充
        :param job:
        :param job_detail:
        :return:
        """
        meta = JobTools.unzip_job_type(job.job_type)
        if meta["step_type"] == constants.SubStepType.PLUGIN:
            subscription = models.Subscription.objects.get(id=job.subscription_id, show_deleted=True)
            meta.update(
                {
                    "name": subscription.name,
                    # 任务类型基础上的进一步类别划分，比如任务类型为【插件】，category{None: 普通插件任务，policy: 策略}
                    "category": subscription.category,
                    "plugin_name": subscription.plugin_name,
                }
            )
            meta["plugin_name"] = subscription.plugin_name

        job_detail["meta"] = meta

    @classmethod
    def fill_cost_time(cls, source: Dict[str, Any], detail: Dict[str, Any]) -> None:
        if not source.get("start_time"):
            return

        if not source.get("end_time"):
            detail["cost_time"] = f'{(timezone.now() - source["start_time"]).seconds}'
        else:
            detail["cost_time"] = f'{(source["end_time"] - source["start_time"]).seconds}'

    @classmethod
    def list_sub_task_related_jobs(cls, subscription_ids: List[int], task_ids: List[int]) -> List[models.Job]:
        jobs_untreated = models.Job.objects.filter(subscription_id__in=set(subscription_ids))

        return [job for job in jobs_untreated if set(job.task_id_list) & set(task_ids)]

    @classmethod
    def fetch_values_from_conditions(cls, conditions: List[Dict], key: str) -> List:
        """获取查询条件列表中某个查询条件的查询值"""
        values = []
        for condition in conditions:
            if condition["key"] != key:
                continue
            try:
                values.extend(list(condition["value"]))
            except Exception:
                values.append(condition["value"])

        return list(set(values))
