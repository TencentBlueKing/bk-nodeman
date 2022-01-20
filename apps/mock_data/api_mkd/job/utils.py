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
from common.api import JobApi

from ... import utils
from . import unit


class JobApiMockClient(utils.BaseMockClient):
    def __init__(
        self,
        fast_execute_script_return=None,
        fast_transfer_file_return=None,
        push_config_file_return=None,
        get_job_instance_status_return=None,
        get_job_instance_ip_log_return=None,
        create_credential_return=None,
        create_file_source_return=None,
    ):

        super().__init__()

        # 操作类接口返回结构基本一致，如果没有具体指定，使用默认值返回
        default_op_interface_return = utils.MockReturn(
            return_type=utils.MockReturnType.RETURN_VALUE.value, return_obj=unit.OP_DATA
        )
        self.fast_execute_script = self.generate_magic_mock(
            mock_return_obj=fast_execute_script_return or default_op_interface_return
        )
        self.fast_transfer_file = self.generate_magic_mock(
            mock_return_obj=fast_transfer_file_return or default_op_interface_return
        )
        self.push_config_file = self.generate_magic_mock(
            mock_return_obj=push_config_file_return or default_op_interface_return
        )
        self.get_job_instance_status = self.generate_magic_mock(mock_return_obj=get_job_instance_status_return)
        self.get_job_instance_ip_log = self.generate_magic_mock(mock_return_obj=get_job_instance_ip_log_return)
        self.create_credential = self.generate_magic_mock(mock_return_obj=create_credential_return)
        self.create_file_source = self.generate_magic_mock(mock_return_obj=create_file_source_return)

        # 记录接口调用
        self.fast_execute_script = self.call_recorder.start(self.fast_execute_script, key=JobApi.fast_execute_script)
        self.fast_transfer_file = self.call_recorder.start(self.fast_transfer_file, key=JobApi.fast_transfer_file)
        self.push_config_file = self.call_recorder.start(self.push_config_file, key=JobApi.push_config_file)
