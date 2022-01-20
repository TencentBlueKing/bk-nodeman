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
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.generic import APIViewSet
from apps.node_man.exceptions import NotSuperUserError
from apps.node_man.handlers.iam import IamHandler
from apps.node_man.handlers.meta import MetaHandler
from apps.node_man.serializers.meta import JobSettingSerializer
from apps.utils.local import get_request_username


class MetaViews(APIViewSet):
    @action(detail=False)
    def filter_condition(self, request):
        """
        @api {GET} /meta/filter_condition/ 获取过滤条件
        @apiName get_filter_condition
        @apiGroup Meta
        @apiParam {String} category 支持: host, job, plugin
        @apiSuccessExample {Json} 成功返回:
        [
            {
                "name": "操作系统",
                "id": "os_type",
                "children": [
                    {
                        "name": "Linux",
                        "id": "Linux"
                    },
                    {
                        "name": "Windows",
                        "id": "Windows"
                    }
                ]
            },
            {
                "name": "Agent状态",
                "id": "version",
                "children": [
                    {
                        "name": "正常",
                        "id": "RUNNING"
                    },
                    {
                        "name": "未知",
                        "id": "UNKNOWN"
                    }
                ]
            }
        ]
        """
        category = request.query_params.get("category", default="")
        result = MetaHandler().filter_condition(category)
        return Response(result)

    @action(detail=False)
    def global_settings(self, request, *args, **kwargs):
        """
        @api {GET} /meta/global_settings/ 查询全局配置
        @apiName retrieve_global_settings
        @apiGroup Meta
        @apiParam {String="isp", "job_settings"} key 键值
        @apiSuccessExample {json} 成功返回:
        [
            {
                "isp": "tencent",
                "isp_name": "腾讯云",
                "isp_icon": "xxxx"
            }
        ]
        """

        key = request.query_params.get("key", default="")
        settings = MetaHandler().search(key)
        return Response(settings)

    @action(detail=False, methods=["POST"], serializer_class=JobSettingSerializer)
    def job_settings(self, request, *args, **kwargs):
        """
        @api {POST} /meta/job_settings/ 任务配置接口
        @apiName job_settings
        @apiGroup Meta
        @apiParam {Int} install_p_agent_timeout 安装P-Agent超时时间
        @apiParam {Int} install_agent_timeout 安装Agent超时时间
        @apiParam {Int} install_proxy_timeout 安装Proxy超时时间
        @apiParam {Int} install_download_limit_speed 安装下载限速
        @apiParam {Int} parallel_install_number 并行安装数
        @apiParam {String} node_man_log_level 节点管理日志级别
        """

        if IamHandler.globe_task_config(get_request_username()):
            MetaHandler().job_setting(self.validated_data)
            return Response()
        raise NotSuperUserError(_("您没有权限修改任务配置"))
