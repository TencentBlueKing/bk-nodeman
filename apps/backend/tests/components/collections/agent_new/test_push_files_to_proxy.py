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

import os.path
from typing import Any, Dict

from django.conf import settings

from apps.backend.components.collections.agent_new import components
from apps.node_man import constants
from common.api import JobApi

from . import base


class PushUpgradePackageTestCase(base.JobBaseTestCase):
    def structure_common_inputs(self) -> Dict[str, Any]:
        common_inputs = super().structure_common_inputs()
        common_inputs.update(
            {"file_list": constants.FILES_TO_PUSH_TO_PROXY[1]["files"], "file_target_path": settings.DOWNLOAD_PATH}
        )
        return common_inputs

    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发文件到Proxy"

    def component_cls(self):
        return components.PushFilesToProxyComponent

    def tearDown(self) -> None:
        record = self.job_api_mock_client.call_recorder.record
        fast_transfer_file_query_params = record[JobApi.fast_transfer_file][0].args[0]
        self.assertListEqual(
            fast_transfer_file_query_params["file_source_list"][0]["file_list"],
            [
                os.path.join(settings.DOWNLOAD_PATH, file_name)
                for file_name in constants.FILES_TO_PUSH_TO_PROXY[1]["files"]
            ],
            is_sort=True,
        )
        super().tearDown()
