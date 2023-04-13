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

import copy
import csv
import os.path
import random
import typing
from typing import Dict

import mock

from apps.mock_data.common_unit.host import AP_MODEL_DATA, CLOUD_MODEL_DATA
from apps.node_man import constants, models
from apps.node_man.management.commands.load_env_info import LoadEnvHandler
from apps.node_man.tests.test_pericdic_tasks.mock_data import (
    MOCK_BK_BIZ_ID,
    MOCK_BK_CLOUD_ID,
    MOCK_HOST,
    MOCK_HOST_NUM,
    MOCK_IP,
)
from apps.utils.files import mk_and_return_tmpdir
from apps.utils.unittest.testcase import CustomBaseTestCase

MOCK_NEW_CLOUD_IDS = [MOCK_BK_CLOUD_ID + 1, MOCK_BK_CLOUD_ID + 2]
MOCK_NEW_BIZ_IDS = [MOCK_BK_BIZ_ID + 1, MOCK_BK_BIZ_ID + 2]
MOCK_BK_CLOUD_BASE_NAME = "load_test_cloud"
MOCK_NEW_AP_LIST = [600, 700]
CLOUD_INFO_PATH = "cloud_info.csv"
PROXY_HOST_INFO_PATH = "proxy_host_info.csv"
OFFSET = random.randint(1, 10)
CMDB_OFFSET = 2000000
BK_ENV_NAME = "test_load.com"


class TestLoadEnvInfo(CustomBaseTestCase):
    @classmethod
    def mock_ap_map(cls):
        """
        Mock 接入点映射关系, 不考虑多对一场景
        """
        if hasattr(cls, "ap_map") and getattr(cls, "ap_map"):
            return cls.ap_map
        else:
            ap_map = {ap_id - OFFSET: ap_id for ap_id in MOCK_NEW_AP_LIST}
            setattr(cls, "ap_map", ap_map)
            return ap_map

    @classmethod
    def mock_old_cloud__ap_id_map(cls):
        ap_map = cls.mock_ap_map()
        old_cloud__ap_id_map: typing.Dict[int, int] = {}
        for cloud_id in MOCK_NEW_CLOUD_IDS:
            old_cloud_id = cloud_id - CMDB_OFFSET
            old_cloud__ap_id_map[old_cloud_id] = list(ap_map.keys())[MOCK_NEW_CLOUD_IDS.index(cloud_id)]
        return old_cloud__ap_id_map

    @classmethod
    def init_db(cls):
        """
        构造新环境内的数据, 包括从 CMDB 同步的主机和云区域, 接入点
        """
        mock_host_info = copy.deepcopy(MOCK_HOST)
        mock_host_list = []

        # Mock 十台主机，五台一组，分别在两个云区域, 而且业务 ID 也分别在两个业务
        for i in range(MOCK_HOST_NUM):
            index = 0 if i < MOCK_HOST_NUM / 2 else 1
            mock_host_info["bk_cloud_id"] = MOCK_NEW_CLOUD_IDS[index]
            mock_host_info["bk_biz_id"] = MOCK_NEW_BIZ_IDS[index]
            mock_host_info["node_type"] = constants.NodeType.PAGENT
            mock_host_info["inner_ip"] = f"127.0.{i}.1" if index == 0 else f"127.0.{i}.0"
            mock_host_info["bk_host_id"] = i
            mock_host_info["ap_id"] = constants.DEFAULT_AP_ID
            mock_host_list.append(models.Host(**mock_host_info))

        models.Host.objects.bulk_create(mock_host_list)

        # mock 两个云区域，名字分别是 load_test_cloud_1 和 load_test_cloud_2
        mock_cloud_info = copy.deepcopy(CLOUD_MODEL_DATA)
        mock_cloud_list = []
        for cloud_id in MOCK_NEW_CLOUD_IDS:
            mock_cloud_info["bk_cloud_id"] = cloud_id
            mock_cloud_info["bk_cloud_name"] = f"{MOCK_BK_CLOUD_BASE_NAME}_{cloud_id}"
            mock_cloud_info["ap_id"] = constants.DEFAULT_AP_ID
            mock_cloud_list.append(models.Cloud(**mock_cloud_info))

        models.Cloud.objects.bulk_create(mock_cloud_list)

        # 创建两个接入点
        mock_ap_info = copy.deepcopy(AP_MODEL_DATA)
        mock_ap_list = []
        for ap_id in MOCK_NEW_AP_LIST:
            mock_ap_info["id"] = ap_id
            mock_ap_info["name"] = ap_id
            mock_ap_list.append(models.AccessPoint(**mock_ap_info))

        models.AccessPoint.objects.bulk_create(mock_ap_list)

    @classmethod
    def mock_cloud_csv_file(cls):
        """
        生成云区域的 csv 文件
        """
        tmp_file_path = mk_and_return_tmpdir()
        cloud_info_csv_path = os.path.join(tmp_file_path, CLOUD_INFO_PATH)
        export_field_list = ["bk_cloud_id", "bk_cloud_name", "isp", "ap_id", "creator", "is_visible", "is_deleted"]
        with open(cloud_info_csv_path, "w+") as f:
            writer = csv.writer(f)
            writer.writerow(export_field_list)
            for cloud_id in MOCK_NEW_CLOUD_IDS:
                mock_cloud_info = [
                    cloud_id - CMDB_OFFSET,
                    f"{MOCK_BK_CLOUD_BASE_NAME}_{cloud_id}",
                    CLOUD_MODEL_DATA["isp"],
                    cls.mock_old_cloud__ap_id_map()[cloud_id - CMDB_OFFSET],
                    CLOUD_MODEL_DATA["creator"],
                    CLOUD_MODEL_DATA["is_visible"],
                    CLOUD_MODEL_DATA["is_deleted"],
                ]
                writer.writerow(mock_cloud_info)
        return cloud_info_csv_path

    @classmethod
    def mock_proxy_host_csv_file(cls):
        tmp_file_path = mk_and_return_tmpdir()
        proxy_host_info_csv_path = os.path.join(tmp_file_path, PROXY_HOST_INFO_PATH)
        proxy_export_field_list = [
            "bk_biz_id",
            "bk_cloud_id",
            "inner_ip",
            "outer_ip",
            "login_ip",
            "data_ip",
            "ap_id",
            "inner_ipv6",
            "outer_ipv6",
            "bk_host_id",
        ]
        with open(proxy_host_info_csv_path, "w+") as proxy_csv_file:
            writer = csv.writer(proxy_csv_file)
            writer.writerow(proxy_export_field_list)
            mock_host_index = 0
            bk_cloud_id = MOCK_NEW_CLOUD_IDS[mock_host_index]
            bk_host_id = models.Host.objects.get(inner_ip=MOCK_IP, bk_cloud_id=bk_cloud_id).bk_host_id
            mock_proxy_host_info = [
                MOCK_NEW_BIZ_IDS[mock_host_index] - OFFSET,
                bk_cloud_id - CMDB_OFFSET,
                MOCK_IP,
                MOCK_IP,
                MOCK_IP,
                MOCK_IP,
                MOCK_NEW_AP_LIST[mock_host_index] - OFFSET,
                MOCK_IP,
                MOCK_IP,
                bk_host_id - CMDB_OFFSET,
            ]
            writer.writerow(mock_proxy_host_info)

        return proxy_host_info_csv_path

    @classmethod
    def mock_env_map(cls) -> Dict[str, typing.Union[str, Dict[int, int]]]:
        """
        构造环境映射关系
        # {'ap_map': {1: 2, 3: 4}, 'offset': '2000000', 'bk_biz_map': {1001: 101, 1002: 102}}
        """
        ap_map = {ap_id - OFFSET: ap_id for ap_id in MOCK_NEW_AP_LIST}
        ap_map_str = ""
        for key, value in ap_map.items():
            ap_map_str += f"{key}:{value},"

        ap_map_str = ap_map_str[:-1]

        bk_biz_map = {biz_id: biz_id - OFFSET for biz_id in MOCK_NEW_BIZ_IDS}
        return {"ap_map": ap_map_str, "bk_biz_map": bk_biz_map, "offset": CMDB_OFFSET}

    def setUp(self) -> None:
        self.init_db()
        env_map = self.mock_env_map()
        env_map["ap_map"] = {ap_id - OFFSET: ap_id for ap_id in MOCK_NEW_AP_LIST}

        mock.patch(
            "apps.node_man.management.commands.load_env_info.LoadEnvHandler.get_env_map", return_value=env_map
        ).start()
        super().setUp()

    def test_load_cloud_info(self):
        """
        测试切换当前环境下的云区域接入点 ID
        """
        cloud_info_csv_file = self.mock_cloud_csv_file()

        # 生成环境映射关系
        env_info_map = self.mock_env_map()
        load_handler = LoadEnvHandler(env_name=BK_ENV_NAME, ap_map=env_info_map["ap_map"])

        load_handler.switch_cloud_ap_id(self.mock_ap_map(), cloud_info_csv_file, offset=CMDB_OFFSET)

        old_cloud___ap_id_map = self.mock_old_cloud__ap_id_map()
        for old_cloud_id, old_ap_id in old_cloud___ap_id_map.items():
            # 校验云区域 ap_id
            new_cloud_id = old_cloud_id + CMDB_OFFSET
            new_ap_id = self.mock_ap_map()[old_ap_id]
            cloud_names = models.Cloud.objects.filter(bk_cloud_id=new_cloud_id).values_list("ap_id", flat=True)
            self.assertTrue(new_ap_id in cloud_names)

    def test_switch_host_ap(self):
        """
        测试切换当前环境云区域内的所有主机接入点
        """
        env_info_map = self.mock_env_map()
        cloud_info_csv_file = self.mock_cloud_csv_file()

        load_handler = LoadEnvHandler(env_name=BK_ENV_NAME, ap_map=env_info_map["ap_map"])
        load_handler.switch_host_ap(
            bk_biz_ids=MOCK_NEW_BIZ_IDS,
            offset=CMDB_OFFSET,
            ap_map=self.mock_ap_map(),
            cloud_info_file_path=cloud_info_csv_file,
        )

        old_cloud___ap_id_map = self.mock_old_cloud__ap_id_map()
        bk_cloud_id = MOCK_NEW_CLOUD_IDS[0]
        old_cloud_id = bk_cloud_id - CMDB_OFFSET
        old_ap_id = old_cloud___ap_id_map[old_cloud_id]
        new_ap_id = self.mock_ap_map()[old_ap_id]
        cloud_host_ap_ids = set(
            list(
                models.Host.objects.filter(bk_cloud_id=bk_cloud_id, bk_biz_id__in=MOCK_NEW_BIZ_IDS).values_list(
                    "ap_id", flat=True
                )
            )
        )
        for ap_ids in cloud_host_ap_ids:
            self.assertTrue(ap_ids == new_ap_id)

        # 校验主机数量
        self.assertEqual(
            models.Host.objects.filter(bk_cloud_id=bk_cloud_id, bk_biz_id__in=MOCK_NEW_BIZ_IDS).count(),
            MOCK_HOST_NUM / 2,
        )

    def test_position_proxy_host(self):
        """
        测试切换当前环境下对应的云区域下所有的主机接入点信息
        """
        proxy_host_info_csv_file = self.mock_proxy_host_csv_file()

        env_info_map = self.mock_env_map()

        load_handler = LoadEnvHandler(env_name=BK_ENV_NAME, ap_map=env_info_map["ap_map"])
        load_handler.position_proxy_host(
            bk_biz_ids=MOCK_NEW_BIZ_IDS,
            proxy_info_file_path=proxy_host_info_csv_file,
            offset=CMDB_OFFSET,
            bk_biz_map=env_info_map["bk_biz_map"],
        )
        proxy_host_id = models.Host.objects.get(inner_ip=MOCK_IP, bk_cloud_id=MOCK_NEW_CLOUD_IDS[0]).bk_host_id

        # 校验 Proxy 主机信息
        proxy_host_node_type = models.Host.objects.get(bk_host_id=proxy_host_id).node_type
        self.assertEqual(proxy_host_node_type, constants.NodeType.PROXY)

        # 校验其他主机类型
        other_host_node_type = models.Host.objects.exclude(
            inner_ip=MOCK_IP, bk_cloud_id=MOCK_NEW_CLOUD_IDS[0]
        ).values_list("node_type", flat=True)
        for node_type in other_host_node_type:
            self.assertEqual(node_type, constants.NodeType.PAGENT)
