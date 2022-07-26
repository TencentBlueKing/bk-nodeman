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

HOST_SEARCH_RESPONSE = {
    "total": 3,
    "list": [
        {
            "status": "RUNNING",
            "version": "1.7.15",
            "bk_cloud_id": 0,
            "bk_biz_id": 2,
            "bk_host_id": 2,
            "bk_host_name": "",
            "bk_addressing": "0",
            "os_type": "LINUX",
            "inner_ip": "127.0.0.1",
            "inner_ipv6": "",
            "outer_ip": "",
            "outer_ipv6": "",
            "ap_id": 1,
            "install_channel_id": None,
            "login_ip": "",
            "data_ip": "",
            "created_at": "2022-07-12 18:58:36+0800",
            "updated_at": "2022-07-12 18:58:36+0800",
            "is_manual": True,
            "extra_data": {"bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
            "status_display": "正常",
            "bk_cloud_name": "直连区域",
            "install_channel_name": None,
            "bk_biz_name": "蓝鲸",
            "job_result": {
                "instance_id": "host|instance|host|2",
                "job_id": 1656,
                "status": "FAILED",
                "current_step": "正在重装",
            },
            "identity_info": {},
            "topology": [
                "蓝鲸 / 中控机 / controller_ip",
                "蓝鲸 / 公共组件 / consul",
                "蓝鲸 / 公共组件 / redis",
                "蓝鲸 / 公共组件 / rabbitmq",
                "蓝鲸 / 公共组件 / beanstalk",
                "蓝鲸 / 管控平台 / license",
                "蓝鲸 / 监控平台v3 / monitor",
            ],
            "operate_permission": True,
        }
    ],
}

HOST_BIZ_PROXY_RESPONSE = [
    {
        "bk_cloud_id": 0,
        "bk_addressing": "0",
        "inner_ip": "127.0.0.1",
        "inner_ipv6": "",
        "outer_ip": "",
        "outer_ipv6": "",
        "login_ip": "127.0.0.2",
        "data_ip": "",
        "bk_biz_id": 1,
    },
    {
        "bk_cloud_id": 0,
        "bk_addressing": "0",
        "inner_ip": "127.0.0.3",
        "inner_ipv6": "",
        "outer_ip": "",
        "outer_ipv6": "",
        "login_ip": "127.0.0.4",
        "data_ip": "",
        "bk_biz_id": 1,
    },
]

HOST_PROXY_RESPONSE = [
    {
        "bk_cloud_id": 1,
        "bk_host_id": 1,
        "inner_ip": "127.0.0.1",
        "inner_ipv6": "",
        "outer_ip": "127.0.0.2",
        "outer_ipv6": "",
        "login_ip": "127.0.0.3",
        "data_ip": "",
        "bk_biz_id": 331,
        "is_manual": True,
        "extra_data": {"data_path": "/var/lib/gse", "bt_speed_limit": None, "peer_exchange_switch_for_agent": 1},
        "bk_biz_name": "test",
        "ap_id": 1,
        "ap_name": "默认接入点",
        "status": "TERMINATED",
        "status_display": "异常",
        "version": "",
        "account": "root",
        "auth_type": "MANUAL",
        "port": 22,
        "re_certification": True,
        "job_result": {},
        "pagent_count": 0,
        "permissions": {"operate": True},
    }
]
