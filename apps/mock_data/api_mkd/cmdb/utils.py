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

import mock

from common.api import CCApi

from ... import utils


class CMDBMockClient(utils.BaseMockClient):
    def __init__(
        self,
        add_host_to_resource_return=None,
        search_business_return=None,
        list_biz_hosts_return=None,
        list_hosts_without_biz_return=None,
        find_host_biz_relations_return=None,
        find_host_by_service_template_return=None,
    ):
        super(CMDBMockClient, self).__init__()
        self.cc = mock.MagicMock()
        self.cc.add_host_to_resource = self.generate_magic_mock(mock_return_obj=add_host_to_resource_return)
        self.cc.search_business = self.generate_magic_mock(mock_return_obj=search_business_return)
        self.cc.list_biz_hosts = self.generate_magic_mock(mock_return_obj=list_biz_hosts_return)
        self.cc.list_hosts_without_biz = self.generate_magic_mock(mock_return_obj=list_hosts_without_biz_return)
        self.cc.find_host_biz_relations = self.generate_magic_mock(mock_return_obj=find_host_biz_relations_return)
        self.cc.find_host_by_service_template = self.generate_magic_mock(
            mock_return_obj=find_host_by_service_template_return
        )


class CCApiMockClient(utils.BaseMockClient):
    def __init__(self, bind_host_agent_return=None, unbind_host_agent_return=None):
        super(CCApiMockClient, self).__init__()
        self.bind_host_agent = self.generate_magic_mock(mock_return_obj=bind_host_agent_return)
        self.unbind_host_agent = self.generate_magic_mock(mock_return_obj=unbind_host_agent_return)

        # 记录接口调用
        self.bind_host_agent = self.call_recorder.start(self.bind_host_agent, key=CCApi.bind_host_agent)
        self.unbind_host_agent = self.call_recorder.start(self.unbind_host_agent, key=CCApi.unbind_host_agent)
