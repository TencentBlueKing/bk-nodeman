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
from mock import patch

from apps.backend.components.collections.agent import (
    PushUpgradePackageComponent,
    PushUpgradePackageService,
)
from apps.backend.tests.components.collections.agent import utils
from apps.backend.tests.components.collections.job import utils as job_utils
from apps.node_man import constants, models
from apps.utils.unittest.testcase import CustomBaseTestCase
from pipeline.component_framework.test import (
    ComponentTestCase,
    ComponentTestMixin,
    ExecuteAssertion,
    Patcher,
    ScheduleAssertion,
)

DESCRIPTION = "下发升级包"

COMMON_INPUTS = utils.AgentTestObjFactory.inputs(
    attr_values={"description": DESCRIPTION, "bk_host_id": utils.BK_HOST_ID},
    # 主机信息保持和默认一致
    instance_info_attr_values={},
)

COMMON_INPUTS.update(
    {
        # Job插件需要的inputs参数
        "job_client": {
            "bk_biz_id": utils.DEFAULT_BIZ_ID_NAME["bk_biz_id"],
            "username": utils.DEFAULT_CREATOR,
            "os_type": constants.OsType.LINUX,
        },
        "ip_list": [{"bk_cloud_id": constants.DEFAULT_CLOUD, "ip": utils.TEST_IP}],
        "context": "test",
        # 由执行业务逻辑填充，在此只是展示数据结构
        "file_target_path": "/tmp/test",
        "file_source": [{"files": ["/tmp/REGEX:[a-z]*.txt"]}],
    }
)


class PushUpgradePackageTestService(PushUpgradePackageService):
    id = utils.JOB_TASK_PIPELINE_ID
    root_pipeline_id = utils.INSTANCE_RECORD_ROOT_PIPELINE_ID


class PushUpgradePackageTestComponent(PushUpgradePackageComponent):
    bound_service = PushUpgradePackageTestService


class PushUpgradePackageSuccessTest(CustomBaseTestCase, ComponentTestMixin):
    JOB_MOCK_CLIENT = utils.JobMockClient(
        fast_push_file_return=utils.JOB_INSTANCE_ID_METHOD_RETURN,
        get_job_instance_log_return=utils.JOB_GET_INSTANCE_LOG_RETURN,
    )

    def setUp(self):
        utils.AgentTestObjFactory.init_db()
        # 设置，默认接入点
        default_ap = models.AccessPoint.objects.get(name="默认接入点")
        models.Host.objects.filter(bk_host_id=utils.BK_HOST_ID).update(ap_id=default_ap.id)

        self.job_version = patch(utils.JOB_VERSION_MOCK_PATH, "V3")
        self.job_version.start()

        patch(job_utils.CORE_FILES_JOB_API_PATH, job_utils.JobV3MockApi()).start()

    def component_cls(self):
        return PushUpgradePackageTestComponent

    def cases(self):
        return [
            ComponentTestCase(
                name="下发升级包成功",
                inputs=COMMON_INPUTS,
                parent_data={},
                execute_assertion=ExecuteAssertion(
                    success=True,
                    outputs={
                        "job_instance_id": 10000,
                        "polling_time": 0,
                        "package_name": "gse_client-linux-x86_64_upgrade.tgz",
                    },
                ),
                schedule_assertion=[
                    ScheduleAssertion(
                        success=True,
                        schedule_finished=True,
                        outputs={
                            "job_instance_id": 10000,
                            "polling_time": 0,
                            "package_name": "gse_client-linux-x86_64_upgrade.tgz",
                            "task_result": {
                                "success": [
                                    {
                                        "ip": utils.TEST_IP,
                                        "bk_cloud_id": 0,
                                        "log_content": "success",
                                        "error_code": 0,
                                        "exit_code": 0,
                                    }
                                ],
                                "pending": [],
                                "failed": [],
                            },
                        },
                    ),
                ],
                execute_call_assertion=None,
                patchers=[Patcher(target=utils.JOB_CLIENT_MOCK_PATH, return_value=self.JOB_MOCK_CLIENT)],
            )
        ]
