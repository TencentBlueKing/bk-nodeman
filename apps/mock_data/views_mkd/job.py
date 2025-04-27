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

# 安装请求参数
from django.conf import settings

from apps.mock_data import utils
from apps.mock_data.common_unit import host
from apps.node_man import constants

JOB_INSTALL_REQUEST_PARAMS = {
    "job_type": constants.JobType.INSTALL_AGENT,
    "hosts": [
        {
            "bk_cloud_id": constants.DEFAULT_CLOUD,
            "ap_id": constants.DEFAULT_AP_ID,
            "bk_biz_id": utils.DEFAULT_BK_BIZ_ID,
            "os_type": constants.OsType.LINUX,
            "inner_ip": host.DEFAULT_IP,
            "inner_ipv6": host.DEFAULT_IPV6,
            "outer_ip": host.DEFAULT_IP,
            "outer_ipv6": host.DEFAULT_IPV6,
            "login_ip": host.DEFAULT_IP,
            "data_ip": host.DEFAULT_IP,
            "account": constants.LINUX_ACCOUNT,
            "port": settings.BKAPP_DEFAULT_SSH_PORT,
            "auth_type": constants.AuthType.PASSWORD,
            "password": "password",
            "key": "key",
        }
    ],
    "retention": 1,
}
# 因为MockClient中接口数据定义死了,如需调用使用,深拷贝后update原数据
JOB_REINSTALL_REQUEST_PARAMS = {
    "job_type": constants.JobType.REINSTALL_AGENT,
    "hosts": [
        {
            "bk_host_id": 14110,
            "bk_cloud_id": constants.DEFAULT_CLOUD,
            "ap_id": constants.DEFAULT_AP_ID,
            "install_channel_id": None,
            "bk_biz_id": 100001,
            "os_type": constants.OsType.LINUX,
            "inner_ip": host.DEFAULT_IP,
            "inner_ipv6": host.DEFAULT_IPV6,
            "account": constants.LINUX_ACCOUNT,
            "port": settings.BKAPP_DEFAULT_SSH_PORT,
            "auth_type": constants.AuthType.PASSWORD,
            "password": "password",
        }
    ],
}


JOB_OPERATE_REQUEST_PARAMS = {"job_type": constants.JobType.REINSTALL_AGENT, "bk_host_id": [host.DEFAULT_HOST_ID]}
JOB_OPERATE_REQUEST_PARAMS_WITHOUT_HOST_ID = {
    "job_type": constants.JobType.REINSTALL_AGENT,
    "hosts": [
        {
            "bk_cloud_id": constants.DEFAULT_CLOUD,
            "ap_id": constants.DEFAULT_AP_ID,
            "inner_ip": host.DEFAULT_IP,
        }
    ],
}
