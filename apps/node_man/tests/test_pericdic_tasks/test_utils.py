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
from apps.node_man import constants, models
from apps.node_man.periodic_tasks.utils import (
    get_host_ap_id,
    get_sync_host_ap_map_config,
)
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestPericdicTasksUtils(CustomBaseTestCase):

    SYNC_HOST_AP_MAP_CONFIG = {
        "enable": True,
        "default_ap_id": {
            "V1": 1,
            "V2": 2,
        },
    }

    DEFAULT_V1_AP_ID: int = 1
    DEFAULT_V2_AP_ID: int = 2

    def setUp(self) -> None:
        models.GlobalSettings.set_config(
            key=models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value,
            value={1: self.DEFAULT_V1_AP_ID, -1: self.DEFAULT_V2_AP_ID},
        )
        models.GlobalSettings.set_config(
            key=models.GlobalSettings.KeyEnum.SYNC_HOST_AP_MAP_CONFIG.value,
            value=self.SYNC_HOST_AP_MAP_CONFIG,
        )

    def update_ap_map_config(self, config):
        models.GlobalSettings.update_config(
            key=models.GlobalSettings.KeyEnum.SYNC_HOST_AP_MAP_CONFIG.value, value=config
        )

    def test_get_sync_host_ap_map_config(self, *args, **kwargs):
        # 开启映射配置
        ap_map_config = get_sync_host_ap_map_config()
        self.assertEqual(ap_map_config.enable, True)

        # 未开启映射配置
        self.update_ap_map_config({})
        ap_map_config = get_sync_host_ap_map_config()
        self.assertEqual(ap_map_config.enable, False)

    def test_get_host_ap_id(self, *args, **kwargs):
        # 开启配置
        self.update_ap_map_config(self.SYNC_HOST_AP_MAP_CONFIG)
        ap_map_config = get_sync_host_ap_map_config()
        default_ap_id: int = 10
        ap_id: int = get_host_ap_id(
            default_ap_id=default_ap_id,
            bk_cloud_id=constants.DEFAULT_CLOUD,
            ap_map_config=ap_map_config,
            is_gse2_gray=True,
        )
        self.assertEqual(ap_id, default_ap_id)

        ap_id: int = get_host_ap_id(
            default_ap_id=constants.DEFAULT_AP_ID,
            bk_cloud_id=constants.DEFAULT_CLOUD,
            ap_map_config=ap_map_config,
            is_gse2_gray=True,
        )
        self.assertEqual(ap_id, self.DEFAULT_V2_AP_ID)
