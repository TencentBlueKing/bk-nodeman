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
from typing import Any, Dict

from django.test import TestCase

from apps.core.gray.handlers import GrayHandler
from apps.exceptions import ValidationError
from apps.node_man.management.commands.create_ap_for_gse2 import Command
from apps.node_man.models import AccessPoint
from env.constants import GseVersion


class TestCreateApForGse2(TestCase):
    def test_create_ap_for_gse2(self):
        kwargs: Dict[str, Any] = {"reference_ap_id": -100, "clean_old_map_id": False}
        # 测试参考id不存情况
        try:
            Command().handle(**kwargs)
        except Exception as e:
            self.assertEqual(e.__class__, ValidationError)

        reference_ap_id: int = 1

        # 测试参考id为v1版本
        kwargs.update(reference_ap_id=reference_ap_id)
        Command().handle(**kwargs)
        gray_ap_map: Dict[int, int] = GrayHandler.get_gray_ap_map()
        ap_id_obj_map: Dict[int, AccessPoint] = AccessPoint.ap_id_obj_map()
        gse_v2_ap: AccessPoint = ap_id_obj_map[gray_ap_map[reference_ap_id]]
        # 断言生成的ap版本为V2
        self.assertEqual(gse_v2_ap.gse_version, GseVersion.V2.value)

        # 测试清理掉原来映射 clean_old_map_id
        kwargs.update(clean_old_map_id=True)
        Command().handle(**kwargs)
        self.assertEqual(list(AccessPoint.objects.filter(id=gse_v2_ap.id)), [])
