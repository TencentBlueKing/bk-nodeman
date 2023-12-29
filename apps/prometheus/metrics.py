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

import os

from django_prometheus.conf import NAMESPACE
from prometheus_client import Counter, Gauge, Histogram


def decode_buckets(buckets_list):
    return [float(x) for x in buckets_list.split(",")]


def get_histogram_buckets_from_env(env_name):
    if env_name in os.environ:
        buckets = decode_buckets(os.environ.get(env_name))
    else:
        buckets = (
            0.005,
            0.01,
            0.025,
            0.05,
            0.075,
            0.1,
            0.25,
            0.5,
            0.75,
            1.0,
            2.5,
            5.0,
            7.5,
            10.0,
            15.0,
            20.0,
            25.0,
            50.0,
            75.0,
            100.0,
            float("inf"),
        )
    return buckets


jobs_by_op_type_operate_step = Counter(
    "django_app_jobs_by_operate_step",
    "Count of jobs by operate, step.",
    ["operate", "step"],
    namespace=NAMESPACE,
)


subscriptions_by_object_node_category = Counter(
    "django_app_subscriptions_by_object_node_category",
    "Count of subscriptions by object, node, category.",
    ["object", "node", "category"],
    namespace=NAMESPACE,
)


app_task_jobs_total = Counter(
    name="app_task_jobs_total",
    documentation="Cumulative count of jobs.",
    labelnames=["operate", "step", "from_system"],
    namespace=NAMESPACE,
)

app_task_subscriptions_total = Counter(
    name="app_task_subscriptions_total",
    documentation="Cumulative count of subscriptions.",
    labelnames=["object", "node", "category"],
    namespace=NAMESPACE,
)


app_task_instances_migrate_actions_total = Counter(
    name="app_task_instances_migrate_actions_total",
    documentation="Cumulative count of instances migrate actions per step_id, per action.",
    labelnames=["step_id", "action"],
    namespace=NAMESPACE,
)

app_task_instances_migrate_reasons_total = Counter(
    name="app_task_instances_migrate_reasons_total",
    documentation="Cumulative count of instances migrate reasons per step_id, per reason.",
    labelnames=["step_id", "reason"],
    namespace=NAMESPACE,
)

app_task_get_instances_by_scope_duration_seconds = Histogram(
    name="app_task_get_instances_by_scope_duration_seconds",
    documentation="Histogram of the time (in seconds) each get instances per source",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
    labelnames=["node_type", "object_type", "source"],
)

app_task_engine_running_executes_info = Gauge(
    name="app_task_engine_running_executes",
    documentation="Number of engine running executes per code.",
    labelnames=["code"],
)

app_task_engine_running_schedules_info = Gauge(
    name="app_task_engine_running_schedules",
    documentation="Number of engine running schedules per code.",
    labelnames=["code"],
)

app_task_engine_execute_duration_seconds = Histogram(
    name="app_task_engine_execute_duration_seconds",
    documentation="Histogram of the time (in seconds) each engine execute per code.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
    labelnames=["code"],
)

app_task_engine_schedule_duration_seconds = Histogram(
    name="app_task_engine_schedule_duration_seconds",
    documentation="Histogram of the time (in seconds) each engine schedule per code.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
    labelnames=["code"],
)

app_task_engine_service_run_exceptions_total = Counter(
    name="app_task_engine_service_run_exceptions_total",
    documentation="Cumulative count of engine service run exceptions " "per code, per exc_type, per exc_code.",
    labelnames=["code", "exc_type", "exc_code"],
)

app_task_engine_sub_inst_statuses_total = Counter(
    name="app_task_engine_sub_inst_statuses_total",
    documentation="Cumulative count of engine subscription instance statuses per status.",
    labelnames=["status"],
)

app_task_engine_sub_inst_step_statuses_total = Counter(
    name="app_task_engine_sub_inst_step_statuses_total",
    documentation="Cumulative count of engine subscription instance step statuses "
    "per step_id, step_type, step_num, step_index, gse_version, action, code, status.",
    labelnames=["step_id", "step_type", "step_num", "step_index", "gse_version", "action", "code", "status"],
)

app_task_engine_get_common_data_duration_seconds = Histogram(
    name="app_task_engine_get_common_data_duration_seconds",
    documentation="Histogram of the time (in seconds) each get common data per step_type.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
    labelnames=["step_type"],
)


app_task_engine_set_sub_inst_statuses_duration_seconds = Histogram(
    name="app_task_engine_set_sub_inst_statuses_duration_seconds",
    documentation="Histogram of the time (in seconds) each set subscription instance statuses.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
)

app_task_engine_set_sub_inst_act_statuses_duration_seconds = Histogram(
    name="app_task_engine_set_sub_inst_act_statuses_duration_seconds",
    documentation="Histogram of the time (in seconds) each set subscription instance activity statuses.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_ENGINE_BUCKETS"),
)

app_plugin_render_configs_total = Counter(
    name="app_plugin_render_configs_total",
    documentation="Cumulative count of render plugin configs "
    "per plugin_name, per name, per os, per cpu_arch, per type.",
    labelnames=["plugin_name", "name", "os", "cpu_arch", "source", "type"],
)

app_core_remote_connects_total = Counter(
    name="app_core_remote_connects_total",
    documentation="Cumulative count of remote connects per method,"
    " per username, per port, per auth_type, per os_type, per status",
    labelnames=["method", "username", "port", "auth_type", "os_type", "status"],
)

app_core_remote_connect_exceptions_total = Counter(
    name="app_core_remote_connect_exceptions_total",
    documentation="Cumulative count of remote connect exceptions per method,"
    " per username, per port, per auth_type, per os_type, per exc_type, per exc_code.",
    labelnames=["method", "username", "port", "auth_type", "os_type", "exc_type", "exc_code"],
)

app_core_remote_execute_duration_seconds = Histogram(
    name="app_core_remote_execute_duration_seconds",
    documentation="Histogram of the time (in seconds) each remote execute per method.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["method"],
)

app_core_remote_batch_execute_duration_seconds = Histogram(
    name="app_core_remote_batch_execute_duration_seconds",
    documentation="Histogram of the time (in seconds) each remote batch execute per method.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["method"],
)

app_core_remote_proxy_info = Gauge(
    name="app_core_remote_proxy_info",
    documentation="A metric with a constants '1' value labeled by proxy_name, proxy_ip, bk_cloud_id, paramiko_version",
    labelnames=["proxy_name", "proxy_ip", "bk_cloud_id", "paramiko_version"],
)

app_core_remote_install_exceptions_total = Counter(
    name="app_core_remote_install_exceptions_total",
    documentation="Cumulative count of remote install exceptions per step, per os_type, per node_type",
    labelnames=["step", "os_type", "node_type"],
)

app_core_cache_decorator_requests_total = Counter(
    name="app_core_cache_decorator_requests_total",
    documentation="Cumulative count of cache decorator requests per type, per backend, per method, per get_cache.",
    labelnames=["type", "backend", "method", "get_cache"],
)

app_core_cache_decorator_hits_total = Counter(
    name="app_core_cache_decorator_hits_total",
    documentation="Cumulative count of cache decorator hits per type, per backend, per method.",
    labelnames=["type", "backend", "method"],
)

app_core_cache_decorator_get_duration_seconds = Histogram(
    name="app_core_cache_decorator_get_duration_seconds",
    documentation="Histogram of the time (in seconds) each decorator get cache per type, per backend, per method.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["type", "backend", "method"],
)

app_core_cache_decorator_set_duration_seconds = Histogram(
    name="app_core_cache_decorator_set_duration_seconds",
    documentation="Histogram of the time (in seconds) each decorator set cache per type, per backend, per method.",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CORE_BUCKETS"),
    labelnames=["type", "backend", "method"],
)

app_core_password_requests_total = Counter(
    name="app_core_password_requests_total",
    documentation="Cumulative count of password requests per handler, per is_ok.",
    labelnames=["handler", "is_ok"],
)


app_common_method_requests_total = Counter(
    name="app_common_method_requests_total",
    documentation="Cumulative count of method requests per method, per source.",
    labelnames=["method", "source"],
)

app_resource_watch_events_total = Counter(
    name="app_resource_watch_events_total",
    documentation="Cumulative count of resource watch events per type, per bk_resource, per bk_event_type.",
    labelnames=["type", "bk_resource", "bk_event_type"],
)

app_resource_watch_trigger_total = Counter(
    name="app_resource_watch_trigger_total",
    documentation="Cumulative count of resource watch trigger per method, per bk_biz_id, per debounce_time.",
    labelnames=["method", "bk_biz_id", "debounce_time"],
)

app_resource_watch_biz_events_total = Counter(
    name="app_resource_watch_biz_events_total",
    documentation="Cumulative count of resource watch biz events per bk_biz_id.",
    labelnames=["bk_biz_id"],
)

app_clean_subscription_instance_records_total = Counter(
    name="app_clean_subscription_instance_records_total",
    documentation="Cumulative count of clean subscription instance records delete data per table.",
    labelnames=["table_name"],
)

app_clean_subscription_instance_records_seconds = Histogram(
    name="app_clean_subscription_instance_records_seconds",
    documentation="Histogram of clean subscription instance records per sql",
    buckets=get_histogram_buckets_from_env("BKAPP_MONITOR_METRICS_CLEAN_BUCKETS"),
    labelnames=["sql"],
)
