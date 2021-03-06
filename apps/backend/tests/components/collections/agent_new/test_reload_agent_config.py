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


from apps.backend.components.collections.agent_new import components

from . import base


class ReloadAgentConfigTestCase(base.JobBaseTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "重载Agent配置成功"

    def component_cls(self):
        return components.ReloadAgentConfigComponent


class IpFailedTestCase(base.JobFailedBaseTestCase, ReloadAgentConfigTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "IP执行错误"


class TimeOutTestCase(base.JobTimeOutBaseTestCase, ReloadAgentConfigTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "作业平台执行作业超时"


class TimeOutButSuccessInTheLastQuery(base.JobTimeOutButSuccessInTheLastQuery, ReloadAgentConfigTestCase):
    @classmethod
    def get_default_case_name(cls) -> str:
        return "作业平台执行作业即将超时：最后一次查询已完成"
