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

SUBSCRIPTION_INFO_RESPONSE = [
    {
        "id": 1521,
        "name": "string",
        "enable": False,
        "category": "once",
        "plugin_name": "",
        "bk_biz_scope": [],
        "scope": {
            "bk_biz_id": 2,
            "object_type": "SERVICE",
            "node_type": "TOPO",
            "nodes": [
                {"bk_host_id": 12},
                {"bk_obj_id": "module", "bk_inst_id": 33},
                {"ip": "127.0.0.1", "bk_cloud_id": 0, "bk_supplier_id": 0},
                {
                    "ip": "127.0.0.1",
                    "bk_cloud_id": 1,
                    "instance_info": {
                        "key": "",
                        "port": 22,
                        "ap_id": 1,
                        "account": "root",
                        "os_type": "LINUX",
                        "login_ip": "127.0.0.1",
                        "password": "UWs9",
                        "username": "admin",
                        "auth_type": "PASSWORD",
                        "bk_biz_id": 337,
                        "data_path": "/var/lib/gse",
                        "is_manual": False,
                        "retention": -1,
                        "bk_os_type": "1",
                        "bk_biz_name": "xxxxxx",
                        "bk_cloud_id": 1,
                        "bk_cloud_name": "xxxx",
                        "bt_speed_limit": "",
                        "host_node_type": "PROXY",
                        "bk_host_innerip": "127.0.0.1",
                        "bk_host_outerip": "127.0.0.1",
                        "install_channel_id": 1,
                        "bk_supplier_account": "0",
                        "peer_exchange_switch_for_agent": 1,
                    },
                    "bk_supplier_account": "0",
                },
            ],
        },
        "pid": -1,
        "target_hosts": [{"ip": "127.0.0.1", "bk_cloud_id": "0", "bk_supplier_id": "0"}],
        "steps": [
            {
                "id": "agent",
                "type": "AGENT",
                "config": {"job_type": "INSTALL_AGENT"},
                "params": {"context": {}, "blueking_language": "zh-hans"},
            },
            {
                "id": "main:bkunifylogbeat",
                "type": "PLUGIN",
                "config": {
                    "job_type": "MAIN_INSTALL_PLUGIN",
                    "plugin_name": "bkunifylogbeat",
                    "check_and_skip": True,
                    "plugin_version": "latest",
                    "config_templates": [{"name": "bkunifylogbeat.conf", "is_main": True, "version": "latest"}],
                    "is_version_sensitive": False,
                },
                "params": {"context": {}},
            },
            {
                "id": "mysql_exporter",
                "type": "PLUGIN",
                "config": {
                    "plugin_name": "mysql_exporter",
                    "plugin_version": "2.3",
                    "config_templates": [
                        {"os": "windows", "name": "config.yaml", "version": "2", "cpu_arch": "x86_64"},
                        {"os": "windows", "name": "env.yaml", "version": "2", "cpu_arch": "x86_64"},
                    ],
                },
                "params": {
                    "context": {"--web.listen-host": "127.0.0.1", "--web.listen-port": "{{ control_info.port }}"},
                    "port_range": "9102,10000-10005,20103,30000-30100",
                },
            },
            {
                "id": "bkmonitorbeat",
                "type": "PLUGIN",
                "config": {
                    "plugin_name": "bkmonitorbeat",
                    "plugin_version": "1.7.0",
                    "config_templates": [{"name": "bkmonitorbeat_exporter.yaml", "version": "1"}],
                },
                "params": {
                    "context": {
                        "labels": {
                            "$for": "cmdb_instance.scopes",
                            "$body": {
                                "bk_target_ip": "{{ cmdb_instance.host.bk_host_innerip }}",
                                "bk_target_topo_id": "{{ scope.bk_inst_id }}",
                                "bk_target_cloud_id": "{{ cmdb_instance.host.bk_cloud_id }}",
                                "bk_collect_config_id": 1,
                                "bk_target_topo_level": "{{ scope.bk_obj_id }}",
                                "bk_target_service_category_id": "{{ cmdb_instance.service.service_category_id }}",
                                "bk_target_service_instance_id": "{{ cmdb_instance.service.id }}",
                            },
                            "$item": "scope",
                        },
                        "metrics_url": "XXX",
                    }
                },
            },
        ],
    }
]


SUBSCRIPTION_CREATE_RESPONSE = {"subscription_id": 1, "task_id": 1}
