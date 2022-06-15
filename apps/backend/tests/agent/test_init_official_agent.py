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
import os
import shutil

from django.conf import settings
from django.core.management import call_command

from apps.backend.tests.agent.utils import AgentPkgBaseTestCase
from apps.mock_data import common_unit
from apps.node_man import constants, models


class InitOfficialAgentTestCase(AgentPkgBaseTestCase):
    def test_init_official_agent_command(self):
        """测试导入命令"""
        with self.settings(
            DOWNLOAD_PATH=self.DOWNLOAD_PATH, BK_OFFICIAL_AGENT_INIT_PATH=self.BK_OFFICIAL_AGENT_INIT_PATH
        ):

            shutil.move(
                os.path.join(self.TMP_DIR, "gse_agent", self.mock_agent_pkg_path),
                os.path.join(self.TMP_DIR, settings.BK_OFFICIAL_AGENT_INIT_PATH),
            )
            shutil.move(
                os.path.join(self.TMP_DIR, constants.AgentPackageMap.CERT, common_unit.agent.CERT_PKG_NAME),
                os.path.join(self.TMP_DIR, settings.BK_OFFICIAL_AGENT_INIT_PATH),
            )

            call_command("init_official_agents")
            self.assertTrue(models.GseAgentDesc.objects.all().exists())
            self.assertTrue(
                models.GseAgentDesc.objects.filter(description=common_unit.agent.AGENT_MEDIUM_DESC).exists()
            )
