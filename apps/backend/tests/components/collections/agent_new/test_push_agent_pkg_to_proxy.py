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
import importlib
import ipaddress
import os
import os.path
import shutil

import mock
from django.test import override_settings

from apps.backend.components.collections.agent_new import (
    components,
    push_agent_pkg_to_proxy,
)
from apps.backend.components.collections.agent_new.components import (
    PushAgentPkgToProxyComponent,
)
from apps.mock_data import api_mkd
from apps.mock_data import utils as mock_data_utils
from apps.node_man import constants, models
from common.api import JobApi
from env.constants import GseVersion

from . import base


class PushAgentPackageToProxyTestCase(base.JobBaseTestCase):
    GSE_VERSION = GseVersion.V2.value

    CLOUD_ID = 1
    DOWNLOAD_PATH = "/tmp/data/bkee/public/bknodeman/download"

    def remove_download_path(self):
        if os.path.exists(self.DOWNLOAD_PATH):
            shutil.rmtree(self.DOWNLOAD_PATH)

    def init_ap(self) -> models.AccessPoint:
        ap_obj = self.create_ap("测试接入点")
        ap_obj.nginx_path = self.DOWNLOAD_PATH
        ap_obj.gse_version = self.GSE_VERSION
        ap_obj.save()
        os.makedirs(self.DOWNLOAD_PATH, exist_ok=True)
        mock_os_cpu = {
            constants.OsType.LINUX.lower(): [constants.CpuType.x86_64, constants.CpuType.aarch64],
            constants.OsType.WINDOWS.lower(): [constants.CpuType.x86_64],
        }
        for os_type, cpu_arch_list in mock_os_cpu.items():
            for cpu_arch in cpu_arch_list:
                os.makedirs(os.path.join(self.DOWNLOAD_PATH, "agent", os_type, cpu_arch), exist_ok=True)
        return ap_obj

    def init_hosts(self):
        ap_obj = self.init_ap()
        self.init_alive_proxies(bk_cloud_id=self.CLOUD_ID, gse_version=self.GSE_VERSION)
        install_channel, jump_server_host_ids = self.create_install_channel()
        self.jump_server_host_ids = set(jump_server_host_ids)
        models.Host.objects.filter(bk_host_id__in=self.obj_factory.bk_host_ids).update(ap_id=ap_obj.id)
        models.Host.objects.filter(bk_host_id=self.obj_factory.bk_host_ids[0]).update(
            os_type=constants.OsType.LINUX,
            node_type=constants.NodeType.PAGENT,
            bk_cloud_id=self.CLOUD_ID,
        )
        models.Host.objects.filter(bk_host_id=self.obj_factory.bk_host_ids[1]).update(
            os_type=constants.OsType.WINDOWS,
            node_type=constants.NodeType.PAGENT,
            bk_cloud_id=self.CLOUD_ID,
        )
        models.Host.objects.filter(bk_host_id=self.obj_factory.bk_host_ids[2]).update(
            os_type=constants.OsType.LINUX,
            node_type=constants.NodeType.AGENT,
            install_channel_id=install_channel.id,
        )

    @classmethod
    def setup_obj_factory(cls):
        """设置 obj_factory"""
        cls.obj_factory.init_host_num = 3

    @staticmethod
    def list_hosts_without_biz_func(params):
        server_ips = params["host_property_filter"]["rules"][0]["value"]
        return {
            "count": [server_ips],
            "info": [
                {"bk_host_id": int(ipaddress.IPv4Address(server_ip)), "bk_host_innerip": server_ip}
                for server_ip in server_ips
            ],
        }

    def init_mock_clients(self):
        self.cmdb_mock_client = api_mkd.cmdb.utils.CCApiMockClient(
            list_hosts_without_biz_return=mock_data_utils.MockReturn(
                return_type=mock_data_utils.MockReturnType.SIDE_EFFECT.value,
                return_obj=self.list_hosts_without_biz_func,
            ),
        )

        mock.patch(
            "apps.backend.agent.tools.get_gse_api_helper",
            api_mkd.gse.utils.get_gse_api_helper(self.GSE_VERSION, api_mkd.gse.utils.GseApiMockClient()),
        ).start()
        super().init_mock_clients()

    def structure_common_inputs(self):
        inputs = super().structure_common_inputs()
        inputs["meta"] = {"GSE_VERSION": self.GSE_VERSION}
        return inputs

    @classmethod
    def get_default_case_name(cls) -> str:
        return "下发 Agent 包到 Proxy（混合场景）"

    def component_cls(self):
        importlib.reload(push_agent_pkg_to_proxy)
        PushAgentPkgToProxyComponent.bound_service = components.PushAgentPkgToProxyService
        return PushAgentPkgToProxyComponent

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.obj_factory.init_gse_package_desc()
        sub_step_obj: models.SubscriptionStep = cls.obj_factory.sub_step_objs[0]
        sub_step_obj.config.update({"name": "gse_agent", "version": "2.0.0"})
        sub_step_obj.save()

    def setUp(self) -> None:
        self.remove_download_path()
        self.init_hosts()
        self.init_mock_clients()
        super().setUp()

    @override_settings(BKAPP_ENABLE_DHCP=True)
    def test_component(self):
        super().test_component()

    def tearDown(self) -> None:
        self.remove_download_path()
        record = self.job_api_mock_client.call_recorder.record
        self.assertEqual(len(record[JobApi.fast_transfer_file]), 3)
        proxies = models.Host.objects.filter(bk_cloud_id=self.CLOUD_ID, node_type=constants.NodeType.PROXY)
        proxy_host_ids = set(proxies.values_list("bk_host_id", flat=True))
        # 由于有不同路径的目标目录，所以会生成多个作业平台任务
        for job_record in record[JobApi.fast_transfer_file]:
            fast_transfer_file_query_params = job_record.args[0]
            # 目标机器必须是 linux
            self.assertEqual(fast_transfer_file_query_params["os_type"], constants.OsType.LINUX)

            file_target_path = fast_transfer_file_query_params["file_target_path"]
            file_list = fast_transfer_file_query_params["file_source_list"][0]["file_list"]
            target_server_ids = set(fast_transfer_file_query_params["target_server"]["host_id_list"])
            # 根据 self.init_hosts 构造出来的数据，必然会产生三个作业对应三个目录
            if file_target_path == "/tmp/data/bkee/public/bknodeman/download/agent/linux/x86_64":
                self.assertEqual(
                    file_list, ["/tmp/data/bkee/public/bknodeman/download/agent/linux/x86_64/gse_agent-2.0.0.tgz"]
                )
                self.assertSetEqual(target_server_ids, proxy_host_ids | self.jump_server_host_ids)
            elif file_target_path == "/tmp/data/bkee/public/bknodeman/download/agent/linux/aarch64":
                self.assertEqual(
                    file_list, ["/tmp/data/bkee/public/bknodeman/download/agent/linux/aarch64/gse_agent-2.0.0.tgz"]
                )
                self.assertSetEqual(target_server_ids, proxy_host_ids | self.jump_server_host_ids)

            elif file_target_path == "/tmp/data/bkee/public/bknodeman/download/agent/windows/x86_64":
                self.assertEqual(
                    file_list, ["/tmp/data/bkee/public/bknodeman/download/agent/windows/x86_64/gse_agent-2.0.0.tgz"]
                )
                self.assertSetEqual(target_server_ids, set(proxy_host_ids))

            else:
                raise AssertionError(f"file_target_path:{file_target_path} is not expected in this test case")
            super().tearDown()
