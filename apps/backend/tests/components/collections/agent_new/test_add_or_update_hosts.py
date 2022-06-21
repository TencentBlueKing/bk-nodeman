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

import copy
import importlib
import random
from typing import Dict, List, Optional, Set

import mock

from apps.backend.components.collections.agent_new import add_or_update_hosts
from apps.backend.components.collections.agent_new.components import (
    AddOrUpdateHostsComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from pipeline.component_framework.test import ComponentTestCase, ExecuteAssertion

from . import utils


class AddOrUpdateHostsTestCase(utils.AgentServiceBaseTestCase):

    CC_API_MOCK_PATHS: List[str] = ["apps.backend.components.collections.agent_new.add_or_update_hosts.CCApi"]

    current_host_id: Optional[int] = None
    host_ids_with_dynamic_ip: Set[int] = None
    to_be_added_host_ids: Set[int] = None
    to_be_updated_host_ids: Set[int] = None
    search_business_result: Optional[Dict] = None
    list_hosts_without_biz_result: Optional[Dict] = None
    add_host_to_business_idle_result: Optional[Dict] = None
    cmdb_mock_client: Optional[api_mkd.cmdb.utils.CCApiMockClient] = None

    def add_host_to_business_idle_func(self, query_params):
        host_num = len(query_params["bk_host_list"])
        if self.current_host_id is None:
            current_host_id = max(models.Host.objects.values_list("bk_host_id", flat=True))
        else:
            current_host_id = self.current_host_id
        self.current_host_id = current_host_id + host_num
        return {"bk_host_ids": list(range(current_host_id + 1, self.current_host_id + 1))}

    @staticmethod
    def find_host_biz_relations_func(query_params):
        bk_host_ids = query_params["bk_host_id"]
        host_biz_relations = []
        for bk_host_id in bk_host_ids:
            host_biz_relation = copy.deepcopy(api_mkd.cmdb.unit.CMDB_HOST_BIZ_RELATION)
            host_biz_relation.update({"bk_host_id": bk_host_id})
            host_biz_relations.append(host_biz_relation)
        return host_biz_relations

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 255

    @classmethod
    def structure_cmdb_mock_data(cls):
        """
        构造CMDB接口返回数据
        :return:
        """
        cls.to_be_updated_host_ids = set(
            random.sample(cls.obj_factory.bk_host_ids, k=random.randint(10, cls.obj_factory.init_host_num))
        )
        cls.to_be_added_host_ids = set(cls.obj_factory.bk_host_ids) - cls.to_be_updated_host_ids

        host_id__obj_map: Dict[int, models.Host] = {
            host_obj.bk_host_id: host_obj for host_obj in cls.obj_factory.host_objs
        }

        host_infos: List[Dict] = []
        cls.host_ids_with_dynamic_ip = set()
        for bk_host_id in cls.to_be_updated_host_ids:
            bk_addressing = random.choice(constants.CmdbAddressingType.list_member_values())
            host_obj = host_id__obj_map[bk_host_id]
            host_info: Dict = copy.deepcopy(api_mkd.cmdb.unit.CMDB_HOST_INFO)
            host_info.update(
                {
                    "bk_host_id": bk_host_id,
                    "bk_addressing": bk_addressing,
                    "bk_host_innerip": host_obj.inner_ip,
                    "bk_host_outerip": host_obj.outer_ipv6,
                    "bk_host_innerip_v6": host_obj.inner_ipv6,
                    "bk_host_outerip_v6": host_obj.outer_ipv6,
                }
            )
            host_infos.append(host_info)
            # 如果是动态寻址，模拟主机不存在的情况，此时会走新增策略
            if bk_addressing == constants.CmdbAddressingType.DYNAMIC.value:
                cls.host_ids_with_dynamic_ip.add(bk_host_id)

        cls.search_business_result = copy.deepcopy(api_mkd.cmdb.unit.SEARCH_BUSINESS_DATA)
        cls.list_hosts_without_biz_result = {"count": len(host_infos), "info": host_infos}

    @classmethod
    def adjust_test_data_in_db(cls):
        """
        调整DB中的测试数据
        :return:
        """
        models.Host.objects.filter(bk_host_id__in=cls.to_be_added_host_ids).delete()

        models.Host.objects.filter(bk_host_id__in=cls.host_ids_with_dynamic_ip).update(
            bk_addressing=constants.CmdbAddressingType.DYNAMIC.value
        )

        for sub_inst_obj in cls.obj_factory.sub_inst_record_objs:
            bk_host_id = sub_inst_obj.instance_info["host"]["bk_host_id"]
            if bk_host_id in cls.to_be_added_host_ids:
                sub_inst_obj.instance_info["host"].pop("bk_host_id")
            if bk_host_id in cls.host_ids_with_dynamic_ip:
                sub_inst_obj.instance_info["host"].pop("bk_host_id")
                sub_inst_obj.instance_info["host"]["bk_addressing"] = constants.CmdbAddressingType.DYNAMIC.value

        models.SubscriptionInstanceRecord.objects.bulk_update(
            cls.obj_factory.sub_inst_record_objs, fields=["instance_info"]
        )

    @classmethod
    def get_default_case_name(cls) -> str:
        return AddOrUpdateHostsComponent.name

    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CCApiMockClient(
            search_business_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value, return_obj=self.search_business_result
            ),
            list_hosts_without_biz_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.RETURN_VALUE.value,
                return_obj=self.list_hosts_without_biz_result,
            ),
            find_host_biz_relations_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.find_host_biz_relations_func,
            ),
            add_host_to_business_idle_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.add_host_to_business_idle_func,
            ),
        )

    def fetch_succeeded_sub_inst_ids(self) -> List[int]:
        return self.common_inputs["subscription_instance_ids"]

    def start_patch(self):
        for client_v2_mock_path in self.CC_API_MOCK_PATHS:
            mock.patch(client_v2_mock_path, self.cmdb_mock_client).start()

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # 初始化DB数据后再修改
        cls.structure_cmdb_mock_data()
        cls.adjust_test_data_in_db()

    def setUp(self) -> None:
        self.init_mock_clients()
        super().setUp()
        self.start_patch()

    def cases(self):
        return [
            ComponentTestCase(
                name=self.get_default_case_name(),
                inputs=self.common_inputs,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=bool(self.fetch_succeeded_sub_inst_ids()),
                    outputs={"succeeded_subscription_instance_ids": self.fetch_succeeded_sub_inst_ids()},
                ),
                schedule_assertion=None,
                execute_call_assertion=None,
            )
        ]

    def component_cls(self):
        importlib.reload(add_or_update_hosts)
        AddOrUpdateHostsComponent.bound_service = add_or_update_hosts.AddOrUpdateHostsService
        self.start_patch()
        return AddOrUpdateHostsComponent

    def assert_in_teardown(self):

        sub_insts = models.SubscriptionInstanceRecord.objects.filter(id__in=self.obj_factory.sub_inst_record_ids)
        all_host_ids = list(
            set([sub_inst.instance_info["host"]["bk_host_id"] for sub_inst in sub_insts] + self.obj_factory.bk_host_ids)
        )
        # 动态 IP 都采用新增策略，最后同步到节点管理的主机会增加
        expect_host_num = len(self.obj_factory.bk_host_ids) + len(self.host_ids_with_dynamic_ip)
        host_objs = models.Host.objects.filter(bk_host_id__in=all_host_ids)

        self.assertEqual(len(host_objs), expect_host_num)
        # 由于原先没有创建相应的进程状态，此处进程状态记录
        self.assertEqual(
            models.ProcessStatus.objects.filter(
                bk_host_id__in=all_host_ids,
                name=models.ProcessStatus.GSE_AGENT_PROCESS_NAME,
                source_type=models.ProcessStatus.SourceType.DEFAULT,
            ).count(),
            self.obj_factory.init_host_num,
        )

        host_id__host_obj_map: Dict[int, models.Host] = {host_obj.bk_host_id: host_obj for host_obj in host_objs}
        for sub_inst in sub_insts:
            host_info = sub_inst.instance_info["host"]
            bk_host_id = host_info["bk_host_id"]
            host_obj = host_id__host_obj_map[bk_host_id]
            # 动态 IP 新增主机后，原来的 bk_host_id 会被更新
            self.assertFalse(bk_host_id in self.host_ids_with_dynamic_ip)
            self.assertEqual(host_info["bk_biz_id"], host_obj.bk_biz_id)
            self.assertEqual(bk_host_id, host_obj.bk_host_id)

    def tearDown(self) -> None:
        self.assert_in_teardown()
        super().tearDown()
