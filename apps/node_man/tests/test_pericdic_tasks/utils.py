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

import contextlib
import copy
from typing import Any, Dict, List, Tuple

from apps.node_man import constants
from common.log import logger

from .. import utils
from . import mock_data


class MockClient(object):
    class gse:
        @classmethod
        def get_proc_status(cls, *args, **kwargs):
            return mock_data.MOCK_GET_PROC_STATUS

        @classmethod
        def get_agent_status(cls, *args, **kwargs):
            return mock_data.MOCK_GET_AGENT_STATUS

        @classmethod
        def get_agent_info(cls, *args, **kwargs):
            return mock_data.MOCK_GET_AGENT_INFO

    class cc(utils.MockClient.cc):
        @classmethod
        def search_cloud_area(cls, *args, **kwargs):
            return mock_data.MOCK_SEARCH_CLOUD_AREA

        @classmethod
        def list_resource_pool_hosts(cls, *args, **kwargs):
            MOCK_HOST_TMP = copy.deepcopy(mock_data.MOCK_HOST)
            count = 2 * mock_data.MOCK_HOST_NUM
            host_list = []
            for index in range(count):
                MOCK_HOST_TMP["bk_host_id"] = index
                MOCK_HOST_TMP["bk_cloud_id"] = index
                MOCK_HOST_TMP["bk_host_innerip"] = MOCK_HOST_TMP["inner_ip"]
                MOCK_HOST_TMP["bk_host_outerip"] = MOCK_HOST_TMP["outer_ip"]
                host_list.append(copy.deepcopy(MOCK_HOST_TMP))

            return_value = {"count": count, "info": host_list}
            return return_value

        @classmethod
        def list_biz_hosts(cls, *args, **kwargs):
            MOCK_HOST_TMP = copy.deepcopy(mock_data.MOCK_HOST)
            MOCK_HOST_TMP["bk_biz_id"] = args[0]["bk_biz_id"]
            MOCK_HOST_TMP["bk_host_innerip"] = MOCK_HOST_TMP["inner_ip"]
            MOCK_HOST_TMP["bk_host_outerip"] = MOCK_HOST_TMP["outer_ip"]
            return_value = {"count": 1, "info": [MOCK_HOST_TMP]}
            return return_value

        @classmethod
        def resource_watch(cls, *args, **kwargs):
            bk_resource = args[0]["bk_resource"]
            bk_event_type = "update"
            bk_detail = copy.deepcopy(mock_data.MOCK_HOST)
            if bk_resource == constants.ResourceType.host:
                # 模拟测试创建/更新主机数据 设置测试更新字段为ip字段
                bk_detail["bk_host_innerip"] = "127.0.0.9"
                bk_detail["bk_host_outerip"] = "127.0.0.9"
            elif bk_resource == constants.ResourceType.host_relation:
                # 模拟测试创建/更新主机关系数据
                bk_detail["bk_biz_id"] = 999
                bk_event_type = "create"
            elif bk_resource == constants.ResourceType.process:
                bk_detail["bk_biz_id"] = 999

            bk_event = {
                "bk_event_type": bk_event_type,
                "bk_resource": bk_resource,
                "bk_detail": bk_detail,
                "bk_cursor": "",
            }
            return_value = {"bk_events": [bk_event], "bk_watched": True}
            return return_value


class MockKazooClient(object):
    def __init__(self, hosts, auth_data, **kwargs):
        self.hosts = hosts
        self.auth_data = auth_data

    def start(self, timeout=15):
        logger.info("The MockKazooClient is starting...")

    def stop(self):
        logger.info("The MockKazonnClient is stoped")

    def get_children(self, path):
        """
        模拟获取当前路径节点下的节点名称
        """
        return mock_data.MOCK_KAZOOCLIENT_CHILDREN_DATA[path]


def check_ip_ports_reachable(host, ports):
    if not all([host, ports]):
        return False
    return True


@contextlib.contextmanager
def modify_constant_data(modify_tuple_list: List[Tuple[Any, Dict]]):
    """
    希望暂时修改mock_data的一些值，
    从而来测试更多的分支
    (item, {attr: value})
    """
    real_tuple_list: List[Tuple[Any, Dict]] = []
    for (item, to_update_attr_map) in modify_tuple_list:
        real_attr_map = {}
        for attr, value in to_update_attr_map.items():
            real_attr_map[attr] = item[attr]
            item[attr] = value

        real_tuple_list.append((item, real_attr_map))

    yield True

    for (item, real_attr_map) in real_tuple_list:
        for attr, value in real_attr_map.items():
            item[attr] = value
