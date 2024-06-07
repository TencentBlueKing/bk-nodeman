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
from django.utils.translation import ugettext_lazy as _

from ..base import DataAPI
from ..domains import BK_NODE_APIGATEWAY_ROOT
from .utils import add_esb_info_before_request


class _BKNodeApi(object):
    MODULE = _("节点管理")
    SIMPLE_MODULE = "NODEMAN"

    def __init__(self):

        self.upload = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/upload/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="上传插件",
            before_request=add_esb_info_before_request,
            api_name="upload",
        )

        self.create_subscription = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/create/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="创建订阅配置",
            before_request=add_esb_info_before_request,
            api_name="create_subscription",
        )
        self.get_subscription_task_status = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/task_result/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查看订阅任务运行状态",
            before_request=add_esb_info_before_request,
            api_name="get_subscription_task_status",
        )
        self.collect_subscription_task_detail = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/collect_task_result_detail/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="采集订阅任务中实例的详细状态",
            before_request=add_esb_info_before_request,
            api_name="collect_subscription_task_detail",
        )
        self.get_subscription_task_detail = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/task_result_detail/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询订阅任务中实例的详细状态",
            before_request=add_esb_info_before_request,
            api_name="get_subscription_task_detail",
        )
        self.check_subscription_task_ready = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/check_task_ready/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询任务是否已准备完成",
            before_request=add_esb_info_before_request,
            api_name="check_subscription_task_ready",
        )
        self.run_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/run/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="执行订阅下发任务",
            before_request=add_esb_info_before_request,
            api_name="run_subscription_task",
        )
        self.subscription_delete = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/delete/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="删除订阅",
            before_request=add_esb_info_before_request,
            api_name="subscription_delete",
        )
        self.subscription_update = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/update/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="更新订阅",
            before_request=add_esb_info_before_request,
            api_name="subscription_update",
        )
        self.subscription_info = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/info/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="订阅详细",
            before_request=add_esb_info_before_request,
            api_name="subscription_info",
        )
        self.subscription_search_policy = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/search_deploy_policy/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询策略列表",
            before_request=add_esb_info_before_request,
            api_name="subscription_search_policy",
        )
        self.subscription_fetch_policy_topo = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/fetch_policy_topo/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件策略拓扑",
            before_request=add_esb_info_before_request,
            api_name="subscription_fetch_policy_topo",
        )
        self.retry_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/retry/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="重试任务",
            before_request=add_esb_info_before_request,
            api_name="retry_subscription_task",
        )
        self.revoke_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/revoke/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="终止正在执行的订阅任务",
            before_request=add_esb_info_before_request,
            api_name="revoke_subscription_task",
        )
        self.fetch_commands = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/fetch_commands/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取安装命令",
            before_request=add_esb_info_before_request,
            api_name="fetch_commands",
        )
        self.retry_node = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/retry_node/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="原子粒度重试任务",
            before_request=add_esb_info_before_request,
            api_name="retry_node",
        )
        # 插件包接口
        self.create_register_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/create_register_task/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="创建注册任务",
            before_request=add_esb_info_before_request,
            api_name="create_register_task",
        )
        self.query_register_task = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/query_register_task/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询插件注册任务",
            before_request=add_esb_info_before_request,
            api_name="query_register_task",
        )
        self.release = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/release/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="发布（上线）插件包",
            before_request=add_esb_info_before_request,
            api_name="release",
        )
        self.package_status_operation = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/package_status_operation/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件包状态类操作",
            before_request=add_esb_info_before_request,
            api_name="package_status_operation",
        )
        self.create_export_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/create_export_task/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="触发插件打包导出",
            before_request=add_esb_info_before_request,
            api_name="create_export_task",
        )
        self.query_export_task = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/query_export_task/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="获取一个导出任务结果",
            before_request=add_esb_info_before_request,
            api_name="query_export_task",
        )
        self.parse = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/parse/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="解析插件包",
            before_request=add_esb_info_before_request,
            api_name="parse",
        )
        self.plugin_list = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件列表",
            before_request=add_esb_info_before_request,
            api_name="plugin_list",
        )
        self.plugin_retrieve = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/{plugin_id}/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件详细",
            before_request=add_esb_info_before_request,
            api_name="plugin_retrieve",
        )
        self.plugin_status_operation = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/plugin_status_operation/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件状态类操作",
            before_request=add_esb_info_before_request,
            api_name="plugin_status_operation",
        )
        self.plugin_history = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/{plugin_id}/history/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="插件包历史",
            before_request=add_esb_info_before_request,
            api_name="plugin_history",
        )
        self.query_host_policy = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/query_host_policy/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="主机策略列表",
            before_request=add_esb_info_before_request,
            api_name="query_host_policy",
        )
        self.migrate_preview = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/migrate_preview/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="变更计算预览",
            before_request=add_esb_info_before_request,
            api_name="migrate_preview",
        )
        self.metric_list = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/healthz/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="自监控指标检查",
            before_request=add_esb_info_before_request,
            api_name="metric_list",
        )
        self.sync_task_create = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/sync_task/create/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="创建同步任务",
            before_request=add_esb_info_before_request,
            api_name="sync_task_create",
        )
        self.sync_task_status = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/sync_task/status/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询同步任务状态",
            before_request=add_esb_info_before_request,
            api_name="sync_task_status",
        )
        self.install = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "/api/job/install/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="安装类任务",
            before_request=add_esb_info_before_request,
            api_name="install",
        )
        self.job_details = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "/api/job/{pk}/details/",
            module=self.MODULE,
            simple_module=self.SIMPLE_MODULE,
            description="查询任务详情",
            before_request=add_esb_info_before_request,
            api_name="job_details",
        )
