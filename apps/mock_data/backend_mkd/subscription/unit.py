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

BK_BIZ_ID = 2

INNER_IP = "127.0.0.1"

BK_CLOUD_ID = 0

BK_SUPPLIER_ID = 0

CONFIG_TEMPLATE_VERSION = 1

PLUGIN_VERSION = 1.1

PLUGIN_NAME = "bkmonitorbeat"

CONFIG_TEMPLATE_NAMES = ["env.yaml", "bkmonitorbeat_script.conf"]

SUBSCRIPTION_DATA = {
    "scope": {
        "bk_biz_id": BK_BIZ_ID,
        "node_type": "INSTANCE",
        "object_type": "HOST",
        "nodes": [{"ip": INNER_IP, "bk_cloud_id": BK_CLOUD_ID, "bk_supplier_id": BK_SUPPLIER_ID}],
    },
    "target_hosts": None,
    "steps": [
        {
            "config": {
                "config_templates": [{"version": CONFIG_TEMPLATE_VERSION, "name": CONFIG_TEMPLATE_NAMES[0]}],
                "plugin_version": PLUGIN_VERSION,
                "plugin_name": "nodeman_performance_test",
            },
            "type": "PLUGIN",
            "id": "nodeman_performance_test",
            "params": {"context": {"cmd_args": ""}},
        },
        {
            "config": {
                "plugin_name": PLUGIN_NAME,
                "plugin_version": "latest",
                "config_templates": [{"name": CONFIG_TEMPLATE_NAMES[1], "version": "latest"}],
            },
            "type": "PLUGIN",
            "id": PLUGIN_NAME,
            "params": {"context": {"cmd_args": ""}},
        },
    ],
}

GSE_PLUGIN_DESC_DATA = {
    "name": PLUGIN_NAME,
    "description": "测试插件啊",
    "scenario": "测试",
    "category": "external",
    "launch_node": "all",
    "config_file": CONFIG_TEMPLATE_NAMES,
    "config_format": "yaml",
    "use_db": False,
}
