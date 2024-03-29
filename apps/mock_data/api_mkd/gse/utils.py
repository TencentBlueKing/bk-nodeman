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

from apps.adapters.api.gse import GSE_HELPERS

from ... import utils
from . import unit


class GseApiMockClient(utils.BaseMockClient):
    DEFAULT_OPERATE_PROC_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.RETURN_VALUE.value, return_obj=unit.OP_RESULT
    )
    DEFAULT_GET_OPERATE_RESULT_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.RETURN_VALUE.value, return_obj=unit.GET_PROC_OPERATE_RESULT
    )
    DEFAULT_GET_AGENT_INFO_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_get_agent_info_return
    )
    DEFAULT_GET_AGENT_STATUS_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_get_agent_status_return
    )
    GET_AGENT_NOT_ALIVE_STATUS_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_get_agent_status_not_alive_return
    )
    DEFAULT_LIST_AGENT_STATE_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_list_agent_state_return
    )
    GET_AGENT_NOT_ALIVE_STATE_LIST_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.RETURN_VALUE.value, return_obj=unit.GET_V2_AGENT_NOT_ALIVE_STATE_LIST
    )
    DEFAULT_GET_PROC_STATUS_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_get_proc_status
    )
    DEFAULT_UPGRADE_TO_AGENT_ID_RETURN = utils.MockReturn(
        return_type=utils.MockReturnType.SIDE_EFFECT.value, return_obj=unit.mock_upgrade_to_agent_id
    )

    def __init__(
        self,
        operate_proc_return=DEFAULT_OPERATE_PROC_RETURN,
        operate_proc_multi_return=DEFAULT_OPERATE_PROC_RETURN,
        get_proc_operate_result_return=DEFAULT_GET_OPERATE_RESULT_RETURN,
        get_proc_status_return=DEFAULT_GET_PROC_STATUS_RETURN,
        sync_proc_status_return=None,
        update_proc_info_return=None,
        get_agent_info_return=DEFAULT_GET_AGENT_INFO_RETURN,
        get_agent_status_return=DEFAULT_GET_AGENT_STATUS_RETURN,
        list_agent_state_return=DEFAULT_LIST_AGENT_STATE_RETURN,
        upgrade_to_agent_id_return=DEFAULT_UPGRADE_TO_AGENT_ID_RETURN,
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
        self.list_agent_state = self.generate_magic_mock(mock_return_obj=list_agent_state_return)
        self.upgrade_to_agent_id = self.generate_magic_mock(mock_return_obj=upgrade_to_agent_id_return)


def get_gse_api_helper(_gse_version: str, gse_api_obj: GseApiMockClient):

    return lambda gse_version: GSE_HELPERS[_gse_version](version=gse_version, gse_api_obj=gse_api_obj)
