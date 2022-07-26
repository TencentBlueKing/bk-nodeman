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
PLUGIN_SEARCH_RESPONSE = {
    "total": 1,
    "list": [
        {
            "bk_biz_id": 2,
            "bk_host_id": 1,
            "bk_cloud_id": 0,
            "bk_host_name": "",
            "bk_addressing": "0",
            "inner_ip": "127.0.0.1",
            "inner_ipv6": "",
            "os_type": "LINUX",
            "cpu_arch": "x86_64",
            "node_type": "Agent",
            "node_from": "NODE_MAN",
            "status": "RUNNING",
            "version": "1.7.19",
            "status_display": "正常",
            "bk_cloud_name": "直连区域",
            "bk_biz_name": "蓝鲸",
            "job_result": {
                "instance_id": "host|instance|host|1",
                "job_id": 1434,
                "status": "SUCCESS",
                "current_step": "正在重装",
            },
            "plugin_status": [{"name": "basereport", "status": "RUNNING", "version": "10.12.76", "host_id": 1}],
            "operate_permission": True,
        }
    ],
}
