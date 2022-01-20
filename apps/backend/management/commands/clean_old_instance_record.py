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
from __future__ import absolute_import, unicode_literals

import json
import time
from typing import Dict, List, Set, Union

from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.models import Q

from apps.backend.management.commands import utils
from apps.node_man import constants, models
from pipeline.engine import models as engine_models

log_and_print = utils.get_log_and_print("clean_old_instance_record")


class CleanType:
    OLD_INSTANCE_RECORD = "old"
    TRANSFER = "transfer"


def list_tree_node_ids(tree, node_ids=None):
    """根据pipeline tree递归得到所有节点id"""
    if node_ids is None:
        node_ids = []

    for flow_id, flow in tree.get("flows", {}).items():
        node_ids.append(flow_id)
        node_ids.append(flow["source"])
        node_ids.append(flow["target"])

    for activity_id, activity in tree.get("activities", {}).items():
        node_ids.append(activity_id)
        if "pipeline" in activity:
            list_tree_node_ids(activity["pipeline"], node_ids)


def clean_pipeline_data(execute_id: int, pipeline_objs: List[models.PipelineTree]):
    """5000 大概 62s"""
    if not pipeline_objs:
        return
    all_node_ids = []
    pipeline_ids = []
    for pipeline_obj in pipeline_objs:
        pipeline_ids.append(pipeline_obj.id)

        node_ids = [pipeline_obj.id]
        list_tree_node_ids(pipeline_obj.tree, node_ids)
        all_node_ids.extend(node_ids)

    del pipeline_objs

    model_delete_num = {}

    model_delete_num["engine.Status"], _ = engine_models.Status.objects.filter(id__in=all_node_ids).delete()
    model_delete_num["engine.Data"], _ = engine_models.Data.objects.filter(id__in=all_node_ids).delete()

    data_ids = set(engine_models.History.objects.filter(identifier__in=all_node_ids).values_list("data_id", flat=True))

    model_delete_num["engine.HistoryData"], _ = engine_models.HistoryData.objects.filter(id__in=data_ids).delete()
    model_delete_num["engine.History"], _ = engine_models.History.objects.filter(identifier__in=all_node_ids).delete()

    model_delete_num["engine.NodeRelationship"], _ = engine_models.NodeRelationship.objects.filter(
        ancestor_id__in=pipeline_ids
    ).delete()

    process_ids = set(
        engine_models.PipelineModel.objects.filter(id__in=pipeline_ids).values_list("process_id", flat=True)
    )
    model_delete_num["engine.PipelineModel"], _ = engine_models.PipelineModel.objects.filter(
        id__in=pipeline_ids
    ).delete()
    model_delete_num["engine.ScheduleService"], _ = engine_models.ScheduleService.objects.filter(
        Q(process_id__in=process_ids) | Q(activity_id__in=all_node_ids)
    ).delete()
    model_delete_num["engine.SubProcessRelationship"], _ = engine_models.SubProcessRelationship.objects.filter(
        process_id__in=process_ids
    ).delete()

    snapshot_ids = set(
        engine_models.PipelineProcess.objects.filter(root_pipeline_id__in=pipeline_ids).values_list(
            "snapshot_id", flat=True
        )
    )
    model_delete_num["engine.ProcessSnapshot"], _ = engine_models.ProcessSnapshot.objects.filter(
        id__in=snapshot_ids
    ).delete()
    model_delete_num["engine.PipelineProcess"], _ = engine_models.PipelineProcess.objects.filter(
        root_pipeline_id__in=pipeline_ids
    ).delete()
    model_delete_num["engine.ProcessCeleryTask"], _ = engine_models.ProcessCeleryTask.objects.filter(
        process_id__in=process_ids
    ).delete()
    model_delete_num["engine.NodeCeleryTask"], _ = engine_models.NodeCeleryTask.objects.filter(
        node_id__in=all_node_ids
    ).delete()

    # Pipeline放在最后删除，防止中途删除异常后无法溯源
    model_delete_num["node_man.PipelineTree"], _ = models.PipelineTree.objects.filter(id__in=pipeline_ids).delete()

    log_and_print(
        f"clean_pipeline_data: pipeline_ids -> {len(pipeline_ids)}, "
        f"delete_num -> {json.dumps(model_delete_num, indent=4)}",
        execute_id=execute_id,
    )


def fetch_pipeline_id_from_global_settings(limit: int) -> Dict[str, List[str]]:
    agent_sub_ids = set(
        models.Job.objects.filter(
            job_type__in=constants.JOB_TYPE_MAP["agent"] + constants.JOB_TYPE_MAP["proxy"]
        ).values_list("subscription_id", flat=True)
    )

    # 先把agent暂存的pipeline删除，这部分pipeline走原来的逻辑，无需处理
    models.GlobalSettings.objects.filter(
        key__in=[f"sub_{agent_sub_id}_to_be_deleted_pipeline_id" for agent_sub_id in agent_sub_ids]
    ).delete()

    global_setting_keys_to_be_deleted = []
    pipeline_ids_to_be_deleted = []
    for k_v in models.GlobalSettings.objects.filter(key__endswith="to_be_deleted_pipeline_id"):
        if isinstance(k_v.v_json, list):
            pipeline_ids_to_be_deleted.extend(k_v.v_json)
            global_setting_keys_to_be_deleted.append(k_v.key)
        if len(pipeline_ids_to_be_deleted) >= limit:
            break

    return {
        "global_setting_keys_to_be_deleted": global_setting_keys_to_be_deleted,
        "pipeline_ids_to_be_deleted": pipeline_ids_to_be_deleted,
    }


def iter2list_str(items: Union[List, Set]):
    # 去除null字段
    list_str = ", ".join([f"'{item}'" for item in list(items) if item])
    return list_str or "null"


def clean_pipeline_data_sql(execute_id, pipeline_objs: List[models.PipelineTree]):

    if not pipeline_objs:
        log_and_print("empty pipeline_objs, skipped", execute_id=execute_id)
        return
    all_node_ids: List[str] = []
    pipeline_ids: List[str] = []
    for pipeline_obj in pipeline_objs:
        pipeline_ids.append(pipeline_obj.id)

        node_ids = [pipeline_obj.id]
        list_tree_node_ids(pipeline_obj.tree, node_ids)
        all_node_ids.extend(node_ids)

    del pipeline_objs

    data_ids: Set[int] = set(
        engine_models.History.objects.filter(identifier__in=all_node_ids).values_list("data_id", flat=True)
    )
    process_ids: Set[str] = set(
        engine_models.PipelineModel.objects.filter(id__in=pipeline_ids).values_list("process_id", flat=True)
    )
    snapshot_ids: Set[int] = set(
        engine_models.PipelineProcess.objects.filter(root_pipeline_id__in=pipeline_ids).values_list(
            "snapshot_id", flat=True
        )
    )

    data_id_list_str, process_id_list_str, snapshot_id_list_str = (
        iter2list_str(data_ids),
        iter2list_str(process_ids),
        iter2list_str(snapshot_ids),
    )
    all_node_id_list_str, pipeline_id_list_str = iter2list_str(all_node_ids), iter2list_str(pipeline_ids)

    table_clean_data = [
        [engine_models.LogEntry._meta.db_table, "node_id", f"({all_node_id_list_str})"],
        [engine_models.Status._meta.db_table, "id", f"({all_node_id_list_str})"],
        [engine_models.Data._meta.db_table, "id", f"({all_node_id_list_str})"],
        [engine_models.HistoryData._meta.db_table, "id", f"({data_id_list_str})"],
        [engine_models.History._meta.db_table, "identifier", f"({all_node_id_list_str})"],
        [engine_models.NodeRelationship._meta.db_table, "ancestor_id", f"({pipeline_id_list_str})"],
        [engine_models.PipelineModel._meta.db_table, "id", f"({pipeline_id_list_str})"],
        [engine_models.SubProcessRelationship._meta.db_table, "process_id", f"({process_id_list_str})"],
        [engine_models.PipelineProcess._meta.db_table, "root_pipeline_id", f"({pipeline_id_list_str})"],
        [engine_models.ProcessSnapshot._meta.db_table, "id", f"({snapshot_id_list_str})"],
        [engine_models.ProcessCeleryTask._meta.db_table, "process_id", f"({process_id_list_str})"],
        [engine_models.NodeCeleryTask._meta.db_table, "node_id", f"({all_node_id_list_str})"],
        # Pipeline放在最后删除，防止中途删除异常后无法溯源
        [models.PipelineTree._meta.db_table, "id", f"({pipeline_id_list_str})"],
    ]

    model_delete_num = {}
    with connection.cursor() as cursor:
        cursor.execute(
            f"delete from {engine_models.ScheduleService._meta.db_table} "
            f"where process_id in ({process_id_list_str}) or activity_id in ({all_node_id_list_str})"
        )
        model_delete_num[engine_models.ScheduleService._meta.db_table] = cursor.rowcount

        for table_to_be_clean in table_clean_data:
            cursor.execute(f"delete from {table_to_be_clean[0]} where {table_to_be_clean[1]} in {table_to_be_clean[2]}")
            model_delete_num[table_to_be_clean[0]] = cursor.rowcount

    log_and_print(
        f"clean_pipeline_data: pipeline_ids -> {len(pipeline_ids)}, "
        f"delete_num -> {json.dumps(model_delete_num, indent=4)}",
        execute_id=execute_id,
    )


def clean_pipeline_data_slice(execute_id: int, pipeline_id_slice: List[str]):
    log_and_print(f"begin to clean slice_size -> {len(pipeline_id_slice)}", execute_id=execute_id)

    try:
        clean_pipeline_data_sql(
            execute_id=execute_id, pipeline_objs=models.PipelineTree.objects.filter(id__in=pipeline_id_slice)
        )
    except Exception as error:
        log_and_print(f"error: {error}", execute_id=execute_id)
        return execute_id
    return None


def clean_old_instance_record_handler(
    pipeline_begin: int = None,
    pipeline_end: int = None,
    clean_type: str = CleanType.OLD_INSTANCE_RECORD,
    limit: int = 500,
) -> str:

    limit = limit or 500

    start_time = time.time()

    global_setting_keys_to_be_deleted = []

    if clean_type == CleanType.TRANSFER:
        fetch_result = fetch_pipeline_id_from_global_settings(limit)
        pipeline_ids_to_be_deleted = fetch_result["pipeline_ids_to_be_deleted"]
        global_setting_keys_to_be_deleted = fetch_result["global_setting_keys_to_be_deleted"]

    else:
        # 仅清理重构前的订阅实例
        pipeline_ids_to_be_deleted = list(
            models.SubscriptionInstanceRecord.objects.filter(is_latest=False, start_pipeline_id="").values_list(
                "pipeline_id", flat=True
            )[pipeline_begin:pipeline_end]
        )

    log_and_print(f"pipeline_ids_to_be_deleted -> {len(pipeline_ids_to_be_deleted)}")

    try:
        clean_pipeline_data_sql(
            execute_id=None, pipeline_objs=models.PipelineTree.objects.filter(id__in=pipeline_ids_to_be_deleted)
        )
        if clean_type == CleanType.TRANSFER:
            models.GlobalSettings.objects.filter(key__in=global_setting_keys_to_be_deleted).delete()
            log_and_print(f"delete global_settings num -> {len(global_setting_keys_to_be_deleted)}")
    except Exception as error:
        log_and_print(f"error: {error}")

    return f"begin -> {pipeline_begin}, end -> {pipeline_end}, total_cost_time -> {round(time.time() - start_time, 2)}s"


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--clean_type",
            nargs="?",
            type=str,
            default=CleanType.OLD_INSTANCE_RECORD,
            choices=[CleanType.OLD_INSTANCE_RECORD, CleanType.TRANSFER],
            help="历史数据清理类型",
        )

        parser.add_argument("--range", nargs=2, type=int, help="pipeline清理范围，--clean_type=old时有效")
        parser.add_argument("--limit", type=int, help="--clean_type=transfer时，指定批量删除数量")

    def handle(self, *args, **options):
        """
        清理老的instance record
        """

        clean_type = options["clean_type"]

        if clean_type == CleanType.OLD_INSTANCE_RECORD and options["range"] is None:
            raise CommandError("--range begin end")

        pipeline_begin, pipeline_end = None, None

        if options.get("range"):
            pipeline_begin, pipeline_end = tuple(options["range"])
            if pipeline_end < pipeline_begin:
                raise CommandError(f"Wrong range -> [{pipeline_begin}, {pipeline_end}]")

        log_content = clean_old_instance_record_handler(
            pipeline_begin=pipeline_begin, pipeline_end=pipeline_end, clean_type=clean_type, limit=options.get("limit")
        )

        log_and_print(log_content)
