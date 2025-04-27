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
import abc
import re
import typing
from collections import ChainMap

from apps.core.concurrent import controller
from apps.node_man import constants, models
from apps.utils import concurrent
from common.api import GseApi

InfoDict = typing.Dict[str, typing.Any]
InfoDictList = typing.List[InfoDict]
AgentIdInfoMap = typing.Dict[str, InfoDict]


class GseApiBaseHelper(abc.ABC):

    version: str = None
    gse_api_obj = None

    def __init__(self, version: str, gse_api_obj=GseApi):
        self.version = version
        self.gse_api_obj = gse_api_obj

    @abc.abstractmethod
    def get_agent_id(self, mixed_types_of_host_info: typing.Union[InfoDict, models.Host]) -> str:
        """
        获取 Agent 唯一标识
        :param mixed_types_of_host_info: 携带主机信息的混合类型对象
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _list_proc_state(
        self,
        namespace: str,
        proc_name: str,
        labels: InfoDict,
        host_info_list: InfoDictList,
        extra_meta_data: InfoDict,
        **options,
    ) -> AgentIdInfoMap:
        """
        获取进程状态信息
        :param namespace: 命名空间
        :param proc_name: 进程名称
        :param labels: 标签
        :param host_info_list: 主机信息列表
        :param extra_meta_data: 额外的元数据
        :param options: 其他可能需要的参数
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _list_agent_state(self, host_info_list: InfoDictList) -> AgentIdInfoMap:
        """
        获取 Agent 状态信息
        :param host_info_list: AgentId - Agent 状态信息映射关系
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def preprocessing_proc_operate_info(self, host_info_list: InfoDictList, proc_operate_info: InfoDict) -> InfoDict:
        """
        进程操作信息预处理
        :param host_info_list: 主机信息列表
        :param proc_operate_info: 进程操作信息
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _operate_proc_multi(self, proc_operate_req: InfoDictList, **options) -> str:
        """
        批量进程操作
        :param proc_operate_req: 进程操作信息列表
        :param options: 其他可能需要的参数
        :return:
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _upgrade_to_agent_id(self, hosts: InfoDictList) -> InfoDict:
        """
        将基于Host IP的配置升级到基于Agent-ID的配置
        :param hosts: 源 hosts 主机信息 [{"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_agent_id": "xxxx"}]
        :return: {"failed":[],"success":["0:127.0.0.1"]}
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_proc_operate_result(self, task_id: str) -> InfoDict:
        """
        获取进程操作结果
        :param task_id: GSE 任务 ID
        :return:
        """
        raise NotImplementedError

    @staticmethod
    def get_version(version_str: typing.Optional[str]) -> str:
        version_str = version_str or ""
        version = version_str.strip().replace(" ", "").replace("\n", "")
        version_pattern = re.compile(r"^[a-zA-Z0-9.-]+$")
        version_match = version_pattern.search(version or "")
        return version_match.group() if version_match else ""

    def get_gse_proc_key(
        self, mixed_types_of_host_info: typing.Union[InfoDict, models.Host], namespace: str, proc_name: str, **options
    ) -> str:
        """
        获取进程唯一标识
        :param mixed_types_of_host_info: 携带主机信息的混合类型对象
        :param namespace: 命名空间
        :param proc_name: 进程名称
        :param options: 其他可能需要的关键字参数
        :return:
        """
        return f"{self.get_agent_id(mixed_types_of_host_info)}:{namespace}:{proc_name}"

    def list_proc_state(
        self,
        namespace: str,
        proc_name: str,
        labels: InfoDict,
        host_info_list: InfoDictList,
        extra_meta_data: InfoDict,
        **options,
    ) -> AgentIdInfoMap:
        """
        获取进程状态信息
        :param namespace: 命名空间
        :param proc_name: 进程名称
        :param labels: 标签
        :param host_info_list: 主机信息列表
        :param extra_meta_data: 额外的元数据
        :param options: 其他可能需要的参数
        :return:
        """

        @controller.ConcurrentController(
            data_list_name="_host_info_list",
            batch_call_func=concurrent.batch_call,
            extend_result=False,
            get_config_dict_func=lambda: {
                "limit": models.GlobalSettings.get_config(
                    key=models.GlobalSettings.KeyEnum.QUERY_PROC_STATUS_HOST_LENS.value,
                    default=constants.QUERY_PROC_STATUS_HOST_LENS,
                )
            },
        )
        def get_proc_status_inner(
            _namespace: str,
            _proc_name: str,
            _labels: InfoDict,
            _host_info_list: InfoDictList,
            _extra_meta_data: InfoDict,
            **_options,
        ) -> typing.List[AgentIdInfoMap]:
            return self._list_proc_state(_namespace, _proc_name, _labels, _host_info_list, _extra_meta_data, **_options)

        agent_id__proc_status_info_map_list: typing.List[AgentIdInfoMap] = get_proc_status_inner(
            _namespace=namespace,
            _proc_name=proc_name,
            _labels=labels,
            _host_info_list=host_info_list,
            _extra_meta_data=extra_meta_data,
            **options,
        )
        return dict(ChainMap(*agent_id__proc_status_info_map_list))

    def list_agent_state(self, host_info_list: InfoDictList) -> AgentIdInfoMap:
        """
        获取 Agent 状态信息
        版本 / 状态
        :param host_info_list: AgentId - Agent 状态信息映射关系
        :return:
        """

        @controller.ConcurrentController(
            data_list_name="_host_info_list",
            batch_call_func=concurrent.batch_call,
            extend_result=False,
            get_config_dict_func=lambda: {"limit": constants.QUERY_AGENT_STATUS_HOST_LENS},
        )
        def list_agent_state_inner(_host_info_list: InfoDictList) -> typing.List[AgentIdInfoMap]:
            return self._list_agent_state(_host_info_list)

        agent_id__agent_state_info_map_list: typing.List[AgentIdInfoMap] = list_agent_state_inner(
            _host_info_list=host_info_list
        )
        return dict(ChainMap(*agent_id__agent_state_info_map_list))

    def operate_proc_multi(self, proc_operate_req: InfoDictList, **options) -> str:
        """
        批量进程操作
        :param proc_operate_req: 进程操作信息列表
        :param options: 其他可能需要的参数
        :return:
        """
        preprocessed_proc_operate_req: InfoDictList = []
        for proc_operate_info in proc_operate_req:
            hosts = proc_operate_info.pop("hosts")
            preprocessed_proc_operate_req.append(self.preprocessing_proc_operate_info(hosts, proc_operate_info))
        return self._operate_proc_multi(preprocessed_proc_operate_req, **options)

    def upgrade_to_agent_id(self, hosts: InfoDictList) -> InfoDict:
        return self._upgrade_to_agent_id(hosts)
