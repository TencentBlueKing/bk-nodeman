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
from apps.adapters.api.gse.base import GseApiBaseHelper
from apps.utils.unittest.testcase import CustomBaseTestCase


class TestGseV2ApiHelper(CustomBaseTestCase):
    def test__list_proc_state(self):
        gse_process_version_sample = " 7 .5 .1.r\n c1 5\n8 "
        version = GseApiBaseHelper.get_version(version_str=gse_process_version_sample)
        self.assertEqual("7.5.1.rc158", version)

        gse_process_version_sample = " 7.5.1-rc15 8 \n "
        version_example = GseApiBaseHelper.get_version(version_str=gse_process_version_sample)
        self.assertEqual("7.5.1-rc158", version_example)

        gse_process_version_sample = " \n 7.5.1 \n  "
        version_example = GseApiBaseHelper.get_version(version_str=gse_process_version_sample)
        self.assertEqual("7.5.1", version_example)

        gse_process_version_sample = "\n 7  \n. \n5 .\n1 \n \n-r\nc 1 5 \n 8 \n "
        version_example = GseApiBaseHelper.get_version(version_str=gse_process_version_sample)
        self.assertEqual("7.5.1-rc158", version_example)
