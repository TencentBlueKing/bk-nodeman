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
from typing import List

from apps.backend.tests.components.collections.agent_new.utils import (
    AgentTestObjFactory,
)
from apps.mock_data import utils
from apps.node_man import models


class GrayTestObjFactory(AgentTestObjFactory):

    GSE_V1_AP_ID: int = -1
    GSE_V2_AP_ID: int = 2

    def structure_gse2_gray_ap_map(self) -> None:
        global_settings_key = models.GlobalSettings.KeyEnum.GSE2_GRAY_AP_MAP.value

        models.GlobalSettings.set_config(key=global_settings_key, value={str(self.GSE_V1_AP_ID): self.GSE_V2_AP_ID})

    def structure_process_status(self):
        bk_host_ids: List[int] = list(models.Host.objects.values_list("bk_host_id", flat=True))
        process_status_objs: List[models.ProcessStatus] = []
        for bk_host_id in bk_host_ids:
            process_status_objs.append(models.ProcessStatus(bk_host_id=bk_host_id, status="RUNNING", name="gseagent"))

        models.ProcessStatus.objects.bulk_create(objs=process_status_objs)

    def init_db(self):
        super().init_db()
        self.structure_gse2_gray_ap_map()
        self.structure_process_status()

    @classmethod
    def structure_biz_gray_data(cls):
        models.Host.objects.update(ap_id=cls.GSE_V2_AP_ID, gse_v1_ap_id=cls.GSE_V1_AP_ID)
        models.GlobalSettings.set_config(
            key=models.GlobalSettings.KeyEnum.GSE2_GRAY_SCOPE_LIST.value, value=[utils.DEFAULT_BK_BIZ_ID]
        )
