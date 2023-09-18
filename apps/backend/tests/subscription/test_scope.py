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

import typing

import mock
from django.test import TestCase

from apps.backend.subscription.tools import covert_biz_set_scope_to_scope
from apps.backend.tests.subscription import utils
from apps.exceptions import ValidationError
from apps.mock_data.utils import DEFAULT_BK_BIZ_ID
from apps.node_man.models import Subscription
from apps.node_man.serializers.base import ScopeSerializer


class TestSubscriptionByScope(TestCase):
    SCOPE_TYPE = Subscription.ScopeType.BIZ_SET
    maxDiff = None

    def setUp(self):
        mock.patch.stopall()
        self.query_limit = mock.patch("apps.node_man.constants.QUERY_CMDB_LIMIT", 10)
        self.handlers_client = mock.patch("apps.node_man.handlers.cmdb.client_v2", utils.BizSetCmdbClient)
        self.handlers_client.start()
        self.query_limit.start()

    def topo__host_scope_with_other_biz(
        self, bk_biz_ids: typing.List[int]
    ) -> typing.Dict[str, typing.Union[str, int, typing.List[typing.Dict[str, typing.Union[str, int]]]]]:
        return {
            "node_type": Subscription.NodeType.TOPO,
            "object_type": Subscription.ObjectType.HOST,
            "scope_type": self.SCOPE_TYPE,
            "scope_id": utils.SCOPE_ID,
            "nodes": [
                {"bk_obj_id": "biz", "bk_inst_id": bk_biz_id, "bk_biz_id": bk_biz_id} for bk_biz_id in bk_biz_ids
            ],
        }

    def topo__host_scope_with_biz_set(self):
        return {
            "node_type": Subscription.NodeType.TOPO,
            "object_type": Subscription.ObjectType.HOST,
            "scope_type": self.SCOPE_TYPE,
            "scope_id": utils.SCOPE_ID,
            "nodes": [{"bk_obj_id": "biz_set", "bk_inst_id": utils.SCOPE_ID}],
        }

    def instance__host_scope(self, bk_biz_ids: typing.List[int]):
        return {
            "node_type": Subscription.NodeType.INSTANCE,
            "object_type": Subscription.ObjectType.HOST,
            "scope_type": self.SCOPE_TYPE,
            "scope_id": utils.SCOPE_ID,
            "nodes": [
                {
                    "bk_host_id": bk_biz_id,
                    "bk_biz_id": bk_biz_id,
                }
                for bk_biz_id in bk_biz_ids
            ],
        }

    def topo__host_scope_with_set(self, bk_biz_ids: typing.List[int]):
        return {
            "node_type": Subscription.NodeType.TOPO,
            "object_type": Subscription.ObjectType.HOST,
            "scope_type": self.SCOPE_TYPE,
            "scope_id": utils.SCOPE_ID,
            "nodes": [
                {
                    "bk_obj_id": "set",
                    "bk_inst_id": bk_biz_id,
                    "bk_biz_id": bk_biz_id,
                }
                for bk_biz_id in bk_biz_ids
            ],
        }

    def set_template__service_scope(self, bk_biz_ids: typing.List[int]):
        return {
            "node_type": Subscription.NodeType.SET_TEMPLATE,
            "object_type": Subscription.ObjectType.SERVICE,
            "scope_type": self.SCOPE_TYPE,
            "scope_id": utils.SCOPE_ID,
            "nodes": [
                {
                    "bk_obj_id": Subscription.NodeType.SET_TEMPLATE,
                    "bk_inst_id": bk_biz_id,
                    "bk_biz_id": bk_biz_id,
                }
                for bk_biz_id in bk_biz_ids
            ],
        }

    def test_covert_biz_set_scope_to_scope(self):
        total_biz_ids = list(set(utils.BIZ_SET_COVERATE_BIZ_IDS + utils.BIZ_SET_NOT_COVERATE_BIZ_IDS))
        # biz_set_scope 过滤后只包括业务集内的 node
        biz_set_scope = self.topo__host_scope_with_other_biz(total_biz_ids)
        covert_biz_set_scope_to_scope(biz_set_scope=biz_set_scope)
        self.assertEqual(biz_set_scope, self.topo__host_scope_with_other_biz(utils.BIZ_SET_COVERATE_BIZ_IDS))

        # 业务集转换为多业务
        biz_set_node_scope = self.topo__host_scope_with_biz_set()
        covert_biz_set_scope_to_scope(biz_set_scope=biz_set_node_scope)
        self.assertEqual(biz_set_node_scope, self.topo__host_scope_with_other_biz(utils.BIZ_SET_COVERATE_BIZ_IDS))

        # 主机范围过滤
        instance__host_scope = self.instance__host_scope(bk_biz_ids=total_biz_ids)
        covert_biz_set_scope_to_scope(biz_set_scope=instance__host_scope)
        self.assertEqual(instance__host_scope, self.instance__host_scope(utils.BIZ_SET_COVERATE_BIZ_IDS))

        # 集群范围过滤
        topo__host_with_set_scope = self.topo__host_scope_with_set(bk_biz_ids=total_biz_ids)
        covert_biz_set_scope_to_scope(biz_set_scope=topo__host_with_set_scope)
        self.assertEqual(topo__host_with_set_scope, self.topo__host_scope_with_set(utils.BIZ_SET_COVERATE_BIZ_IDS))

        # 集群模版过滤
        set_template__service_scope = self.set_template__service_scope(bk_biz_ids=total_biz_ids)
        covert_biz_set_scope_to_scope(biz_set_scope=set_template__service_scope)
        self.assertEqual(set_template__service_scope, self.set_template__service_scope(utils.BIZ_SET_COVERATE_BIZ_IDS))

    def test_biz_set_scope_serializers(self):
        biz_set_scope = self.topo__host_scope_with_other_biz(bk_biz_ids=utils.BIZ_SET_COVERATE_BIZ_IDS)
        self.assertTrue(ScopeSerializer(data=biz_set_scope).is_valid())

        without_biz_nodes = [{"bk_host_id": bk_host_id} for bk_host_id in utils.BIZ_SET_COVERATE_BIZ_IDS]
        biz_set_scope["nodes"] = without_biz_nodes
        # 业务集场景下，所有的 node 都需要包括 bk_biz_id
        self.assertRaises(ValidationError, ScopeSerializer(data=biz_set_scope).is_valid)

        # 业务集指定时， scope id 不能为空
        without_scope_id_scope = self.topo__host_scope_with_other_biz(bk_biz_ids=utils.BIZ_SET_COVERATE_BIZ_IDS)
        del without_scope_id_scope["scope_id"]
        self.assertRaises(ValidationError, ScopeSerializer(data=without_scope_id_scope).is_valid)

        # 多业务集不支持
        muiltple_biz_set_scope: typing.Dict[
            str, typing.Union[str, int, typing.List[typing.Dict[str, typing.Union[str, int]]]]
        ] = self.topo__host_scope_with_other_biz(bk_biz_ids=utils.BIZ_SET_COVERATE_BIZ_IDS)
        muiltple_biz_set_scope["nodes"] = [
            {"bk_obj_id": "biz_set", "bk_inst_id": biz_set_id} for biz_set_id in utils.BIZ_SET_COVERATE_BIZ_IDS
        ]
        self.assertRaises(ValidationError, ScopeSerializer(data=muiltple_biz_set_scope).is_valid)

    def _get_biz_type_scope(self, bk_biz_id: int, nodes=None):
        scope = {
            "node_type": Subscription.NodeType.INSTANCE,
            "object_type": Subscription.ObjectType.HOST,
            "scope_type": Subscription.ScopeType.BIZ,
            "scope_id": bk_biz_id,
        }
        if nodes is None:
            nodes = {"nodes": [{"bk_host_id": bk_host_id} for bk_host_id in utils.BIZ_SET_COVERATE_BIZ_IDS]}
        else:
            nodes = nodes

        return {**scope, **nodes}

    def test_biz_scope_serializers(self):
        # nodes 只包括 host_id
        host_scope = self._get_biz_type_scope(bk_biz_id=DEFAULT_BK_BIZ_ID)
        self.assertTrue(ScopeSerializer(data=host_scope))
        ip__cloud_id_nodes = [
            {"ip": f"127.0.0.{index}", "bk_cloud_id": bk_cloud_id}
            for index, bk_cloud_id in enumerate(utils.BIZ_SET_COVERATE_BIZ_IDS)
        ]
        host_scope["nodes"] = ip__cloud_id_nodes
        self.assertTrue(ScopeSerializer(data=host_scope))
