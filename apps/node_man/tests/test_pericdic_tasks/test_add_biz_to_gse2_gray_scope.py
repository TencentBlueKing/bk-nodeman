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

from apps.node_man.models import GlobalSettings
from apps.node_man.periodic_tasks.add_biz_to_gse2_gray_scope import (
    sync_new_biz_to_gray_scope_list,
)
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestAddBizToGrayScopeList(CustomBaseTestCase):
    def init_db(self):
        GlobalSettings.objects.update_or_create(
            defaults={
                "v_json": [1],
            },
            key=GlobalSettings.KeyEnum.ALL_BIZ_IDS.value,
        )
        GlobalSettings.objects.update_or_create(
            defaults={
                "v_json": [1],
            },
            key=GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value,
        )

    @mock.patch(
        "apps.node_man.periodic_tasks.add_biz_to_gse2_gray_scope.search_business",
        return_value=[{"bk_biz_id": 10, "bk_biz_name": ""}],
    )
    def test_add_biz_to_gse2_gray_scope(self, *args, **kwargs):
        # 未开启同步
        self.assertEqual(sync_new_biz_to_gray_scope_list(), None)

        # 开启同步
        self.init_db()
        sync_new_biz_to_gray_scope_list()
        gse2_gray_scope_list = GlobalSettings.get_config(key=GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value)
        self.assertEqual(10 in gse2_gray_scope_list, True)
        all_biz_ids = GlobalSettings.get_config(key=GlobalSettings.KeyEnum.ALL_BIZ_IDS.value)
        self.assertEqual(all_biz_ids, gse2_gray_scope_list)
