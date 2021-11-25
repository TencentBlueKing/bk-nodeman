# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-节点管理(BlueKing-BK-NODEMAN) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
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

    def __init__(self):

        self.upload = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/upload/",
            module=self.MODULE,
            description="上传插件",
            before_request=add_esb_info_before_request,
        )

        self.create_subscription = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/create/",
            module=self.MODULE,
            description="创建订阅配置",
            before_request=add_esb_info_before_request,
        )
        self.get_subscription_task_status = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/task_result/",
            module=self.MODULE,
            description="查看订阅任务运行状态",
            before_request=add_esb_info_before_request,
        )
        self.collect_subscription_task_detail = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/collect_task_result_detail/",
            module=self.MODULE,
            description="采集订阅任务中实例的详细状态",
            before_request=add_esb_info_before_request,
        )
        self.get_subscription_task_detail = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/task_result_detail/",
            module=self.MODULE,
            description="查询订阅任务中实例的详细状态",
            before_request=add_esb_info_before_request,
        )
        self.run_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/run/",
            module=self.MODULE,
            description="执行订阅下发任务",
            before_request=add_esb_info_before_request,
        )
        self.subscription_delete = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/delete/",
            module=self.MODULE,
            description="删除订阅",
            before_request=add_esb_info_before_request,
        )
        self.subscription_update = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/update/",
            module=self.MODULE,
            description="更新订阅",
            before_request=add_esb_info_before_request,
        )
        self.subscription_info = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/info/",
            module=self.MODULE,
            description="订阅详细",
            before_request=add_esb_info_before_request,
        )
        self.subscription_search_policy = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/search_deploy_policy/",
            module=self.MODULE,
            description="查询策略列表",
            before_request=add_esb_info_before_request,
        )
        self.subscription_fetch_policy_topo = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/fetch_policy_topo/",
            module=self.MODULE,
            description="插件策略拓扑",
            before_request=add_esb_info_before_request,
        )
        self.retry_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/retry/",
            module=self.MODULE,
            description="重试任务",
            before_request=add_esb_info_before_request,
        )
        self.revoke_subscription_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/revoke/",
            module=self.MODULE,
            description="终止正在执行的订阅任务",
            before_request=add_esb_info_before_request,
        )
        self.fetch_commands = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/fetch_commands/",
            module=self.MODULE,
            description="获取安装命令",
            before_request=add_esb_info_before_request,
        )
        self.retry_node = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/retry_node/",
            module=self.MODULE,
            description="原子粒度重试任务",
            before_request=add_esb_info_before_request,
        )
        # 插件包接口
        self.create_register_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/create_register_task/",
            module=self.MODULE,
            description="创建注册任务",
            before_request=add_esb_info_before_request,
        )
        self.query_register_task = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/query_register_task/",
            module=self.MODULE,
            description="查询插件注册任务",
            before_request=add_esb_info_before_request,
        )
        self.release = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/release/",
            module=self.MODULE,
            description="发布（上线）插件包",
            before_request=add_esb_info_before_request,
        )
        self.package_status_operation = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/package_status_operation/",
            module=self.MODULE,
            description="插件包状态类操作",
            before_request=add_esb_info_before_request,
        )
        self.create_export_task = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/create_export_task/",
            module=self.MODULE,
            description="触发插件打包导出",
            before_request=add_esb_info_before_request,
        )
        self.query_export_task = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/query_export_task/",
            module=self.MODULE,
            description="获取一个导出任务结果",
            before_request=add_esb_info_before_request,
        )
        self.parse = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/parse/",
            module=self.MODULE,
            description="解析插件包",
            before_request=add_esb_info_before_request,
        )
        self.plugin_list = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/",
            module=self.MODULE,
            description="插件列表",
            before_request=add_esb_info_before_request,
        )
        self.plugin_retrieve = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/{plugin_id}/",
            module=self.MODULE,
            description="插件详细",
            before_request=add_esb_info_before_request,
        )
        self.plugin_status_operation = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/plugin_status_operation/",
            module=self.MODULE,
            description="插件状态类操作",
            before_request=add_esb_info_before_request,
        )
        self.plugin_history = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/plugin/{plugin_id}/history/",
            module=self.MODULE,
            description="插件包历史",
            before_request=add_esb_info_before_request,
        )
        self.query_host_policy = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/query_host_policy/",
            module=self.MODULE,
            description="主机策略列表",
            before_request=add_esb_info_before_request,
        )
        self.migrate_preview = DataAPI(
            method="POST",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/subscription/migrate_preview/",
            module=self.MODULE,
            description="变更计算预览",
            before_request=add_esb_info_before_request,
        )
        self.metric_list = DataAPI(
            method="GET",
            url=BK_NODE_APIGATEWAY_ROOT + "backend/api/healthz/",
            module=self.MODULE,
            description="自监控指标检查",
            before_request=add_esb_info_before_request,
        )
