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

from ... import utils


class GseApiMockClient(utils.BaseMockClient):
    def __init__(
        self,
        operate_proc_return=None,
        operate_proc_multi_return=None,
        get_proc_operate_result_return=None,
        get_proc_status_return=None,
        sync_proc_status_return=None,
        update_proc_info_return=None,
        get_agent_info_return=None,
        get_agent_status_return=None,
    ):
        super().__init__()
        self.operate_proc = self.generate_magic_mock(mock_return_obj=operate_proc_return)
        self.operate_proc_multi = self.generate_magic_mock(mock_return_obj=operate_proc_multi_return)
        self.get_proc_operate_result = self.generate_magic_mock(mock_return_obj=get_proc_operate_result_return)
        self.get_proc_status = self.generate_magic_mock(mock_return_obj=get_proc_status_return)
        self.sync_proc_status = self.generate_magic_mock(mock_return_obj=sync_proc_status_return)
        self.update_proc_info = self.generate_magic_mock(mock_return_obj=update_proc_info_return)
        self.get_agent_info = self.generate_magic_mock(mock_return_obj=get_agent_info_return)
        self.get_agent_status = self.generate_magic_mock(mock_return_obj=get_agent_status_return)
