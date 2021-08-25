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

from ..base import BaseApi, DataAPI
from ..domains import JOB_APIGATEWAY_ROOT_V3


class _JobApi(BaseApi):
    MODULE = _("作业平台")

    def __init__(self):
        self.fast_execute_script = DataAPI(
            method="POST",
            url=JOB_APIGATEWAY_ROOT_V3 + "fast_execute_script/",
            module=self.MODULE,
            description="快速执行脚本",
        )
        self.fast_transfer_file = DataAPI(
            method="POST",
            url=JOB_APIGATEWAY_ROOT_V3 + "fast_transfer_file/",
            module=self.MODULE,
            description="快速分发文件",
        )
        self.push_config_file = DataAPI(
            method="POST",
            url=JOB_APIGATEWAY_ROOT_V3 + "push_config_file/",
            module=self.MODULE,
            description="快速分发配置",
        )
        self.get_job_instance_status = DataAPI(
            method="GET",
            url=JOB_APIGATEWAY_ROOT_V3 + "get_job_instance_status/",
            module=self.MODULE,
            description="查询作业执行状态",
        )
        self.get_job_instance_ip_log = DataAPI(
            method="GET",
            url=JOB_APIGATEWAY_ROOT_V3 + "get_job_instance_ip_log/",
            module=self.MODULE,
            description="根据作业实例ID查询作业执行日志",
        )
        self.create_credential = DataAPI(
            method="POST",
            url=JOB_APIGATEWAY_ROOT_V3 + "create_credential/",
            module=self.MODULE,
            description="新建凭证",
        )
        self.create_file_source = DataAPI(
            method="POST",
            url=JOB_APIGATEWAY_ROOT_V3 + "create_file_source/",
            module=self.MODULE,
            description="新建文件源",
        )
